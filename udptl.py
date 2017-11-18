
import random
import os
import io
import socket
import select
import threading
from time import time, sleep
#from cjson import encode, decode
from cPickle import loads, dumps
import numpy as np
from collections import OrderedDict
from loggers import get_logger, flush

# TODO: client / server handshaking
# TODO: efective throughput ratio
# TODO: client / server ends (e.g. timeout)
# TODO: scp alike program from command line

DEFAULT_PORT = 20000

log = get_logger(__file__)

def set_logger(logger):
    global log
    log = logger

def parse_address(address):
    address = address.split(':')
    if len(address) < 2:
        port = DEFAULT_PORT
    else:
        port = int(address[1])
    return address[0], port

class TransportLayer(object):
    HEADER = 100

    def __init__(self, timer=10):
        self.handler = dict()
        self.running = None  # not initiated
        self.th_rx = None
        self.timer = timer

    def send(self, uid, data, addr):
        raw = self.pack(uid, data)
        self._send(raw, addr)

    def _send(self, raw, addr):
        raise NotImplementedError()

    def pack(self, uid, data):
        return dumps([uid, data], protocol=2)

    def unpack(self, raw):
        return loads(raw)

    def start(self):
        self.running = True
        self.th_rx = threading.Thread(target=self.run_rx)
        self.th_rx.start()

        self.th_tx = threading.Thread(target=self.run_tx)
        self.th_tx.start()

    def stop(self):
        self.running = False

    def add(self, handler):
        self.handler[handler.uid] = handler
        handler.transport = self

    def remove(self, handler):
        self.handler.pop(handler.uid, None)
        handler.transport = None

    def unknown_handler(self, a, b, uid, data):
        pass


class UDPTL(TransportLayer):
    def __init__(self, address):
        TransportLayer.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = address
        self.sock.bind(self.addr)
        self.tx_pause = 0.0010

    def _send(self, raw, addr):
        # log.debug('%s %s (%s bytes)', uid, addr, len(raw))
        self.sock.sendto(raw, addr)

    def run_rx(self):
        sock = self.sock
        rlist = [sock]
        t0 = 0  # always enters for 1st time

        while self.running:
            r, _, _ = select.select(rlist, [], [], 0.5)
            if r:
                raw, addr = sock.recvfrom(0x4000)
                uid, data = self.unpack(raw)
                handler = self.handler.get(uid)
                if handler:
                    # handler.addr = addr
                    response = handler.dispatch(uid, data, addr)
                else:
                    response = self.unknow_handler(uid, data, addr)

                if response:
                    raw = self.pack(uid, response)
                    self._send(uid, raw, addr)
            else:
                for handler in self.handler.values():
                    handler.idle()

            t1 = time()
            if t1 > t0:
                t0 = t1 + self.timer
                for handler in self.handler.values():
                    handler.timer()

    def run_tx(self):
        sock = self.sock
        while self.running:
            sleep(self.tx_pause)
            for block, handler in self.handler.items():
                response = handler.next_response()
                if response:
                    uid, msg, addr = response
                    # uid = handler.uid
                    raw = self.pack(uid, msg)
                    self._send(raw, addr)
                    sleep(self.tx_pause)
                else:
                    sleep(0.1)


class Handler(object):

    def __init__(self, uid, transport, addr=None):
        self.uid = uid
        self.transport = None
        self.lock = threading.RLock()
        self.addr = addr
        transport.add(self)

    def dispatch(self, a, b, uid, data, *args):
        raise NotImplementedError()

    def idle(self):
        pass

    def timer(self):
        pass


class NETBLT(Handler):
    CMD_END = 'end'
    CMD_RESEND = 'resend'
    CMD_PACKET = 'packet'
    PACKET_SIZE = 2048
    BLOCK_N_PACKETS = 1024
    BLOCK_SIZE = PACKET_SIZE * BLOCK_N_PACKETS
    BLOCK_WINDOW = 4

    def __init__(self, uid, transport, M, addr=None):
        self.M = M
        self.burst = 1.0  # TODO: typically under 0.1
        self.block_attender = OrderedDict()
        blocks = float(M) / self.BLOCK_SIZE
        if blocks != int(blocks):
            blocks += 1
        for index in range(int(blocks)):
            self.block_attender[index] = gen = self.attend(index)
            # force to start and be able to receive responses for 1st time
            gen.next()

        Handler.__init__(self, uid, transport, addr)

    def attend(self, index):
        raise NotImplementedError()

    def dispatch(self, uid, data, *args):
        # print "Message:", uid, data, args
        block = data[1]
        handler = self.block_attender.get(block)
        if handler:
            try:
                with self.lock:
                    response = handler.send(data) or self.next_response()
                return response
            except StopIteration:
                log.info('%s, StopIteration-1, block: %s', self, block)
                self.block_attender.pop(block, None)

    def next_response(self):
        for block, handler in self.block_attender.items():
            try:
                with self.lock:
                    response = handler.next()
                if response:
                    return response
            except StopIteration:
                log.info('%s, StopIteration-2, block: %s', self, block)
                self.block_attender.pop(block, None)  # can continue looping?


class Client(NETBLT):

    def __init__(self, uid, transport, M, addr):
        self.M = M
        self.current = 0
        NETBLT.__init__(self, uid, transport, M, addr)
        self.file = file('output', 'wb')

    def timer(self):
        print "<< Hello from %s" % self
        response = self.next_response()
        if response and self.transport:
            self.transport.send(self.uid, response, self.addr)

    def attend(self, index):
        # t0 = time() + self.burst
        t0 = 0  # always enters for 1st time
        packets = [None] * self.BLOCK_N_PACKETS
        mask = np.zeros(
            shape=(self.BLOCK_N_PACKETS, ),
            dtype=np.bool)

        while not mask.all():
            t1 = time()
            # only send mask
            if index - self.current < self.BLOCK_WINDOW and t1 > t0:
                request = [
                    self.CMD_RESEND,
                    index,
                    np.packbits(mask).tobytes(),
                    self.current
                ]
                t0 = t1 + self.burst
            else:
                request = None

            response = yield request
            if response:
                assert response[1] == index
                if response[0] == self.CMD_PACKET:
                    n = response[2]
                    packets[n] = response[3]
                    mask[n] = 1

        while index != self.current:
            yield None
            foo = 1
        for data in packets:
            self.file.write(data)

        self.file.flush()
        self.current += 1
        foo = 2



class Sender(NETBLT):

    def __init__(self, uid, transport, raw):
        M = raw.seek(0, io.SEEK_END)
        raw.seek(0, io.SEEK_SET)
        NETBLT.__init__(self, uid, transport, M)
        self.raw = raw

    def timer(self):
        print ">> Hello from %s" % self

    def attend(self, index):
        root = index * self.BLOCK_SIZE
        log.info('New Sender.attender: %s', index)
        while True:
            request = yield
            if not request:
                continue

            assert request[1] == index
            if request[0] == self.CMD_RESEND:
                mask = request[2]
                mask = np.frombuffer(mask, dtype=np.uint8)
                mask = np.unpackbits(mask)
                # show the mask as '...XX..XXX.....' sequence


                log.info('< %s %s (%d packets missing)',
                         request[0], request[1], mask.size-mask.sum())
                log.info(''.join([chr(c) for c in (mask * 42 + 46)]))

                for n in np.ravel(np.where(mask==0)):
                    self.raw.seek(root + self.PACKET_SIZE * n)
                    data = self.raw.read(self.PACKET_SIZE)
                    response = [
                        self.CMD_PACKET,
                        index,
                        n,
                        data
                    ]

                    #log.info('> %s %s %s (payload...)', *response[:3])
                    request = yield response
                    if request:
                        log.info('abort sequence, a new command is received')
                        print request[:2]
                        break

        foo = 1





def test_xxx():
    client = UDPTL(20000)
    server = UDPTL(20001)

    client.start()
    server.start()

    # TODO: listen and handshaking protocol
    # TODO: for the test, 'connect' together
    client.where = server.addr

    # create a sample data to be sent
    # M = 10 ** 5
    # raw = os.urandom(M)

    raw = io.FileIO('video.mp4')
    M = raw.seek(0, io.SEEK_END)
    raw.seek(0, io.SEEK_SET)

    # and two peers connected each other
    uid = 'test'
    s = Sender(uid, server, raw)
    c = Client(uid, client, M)

    while True:
        sleep(1)

    client.stop()
    server.stop()

if __name__ == '__main__':
    test_xxx()
