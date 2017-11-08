import random
import os
import io
import types
import socket
import select
import threading
import uuid
import hashlib
from time import time, sleep
from cjson import encode, decode
from collections import OrderedDict, namedtuple
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

CHANNEL = 'channel'
COMMAND = 'command'
MSG_ID = 'mid'
RESPONSE_ID = 'response'
SENDER_ID = 'uid'
BODY = 'body'

CHANNEL_NET = 'net'
CMD_PING = 'ping'

SEND_TIMEOUT = 1

class Message(dict):
    """Plugin messages are simply dictionaries.
    message id
    response flag
    sender id
    channel
    body
"""

class Ping(Message):
    def __init__(self, **kw):
        dict.__init__(self, **kw)
        self[CHANNEL] = CHANNEL_NET
        self[COMMAND] = CMD_PING

def genuid():
    uid = hashlib.sha1(uuid.uuid1().get_hex()).hexdigest()
    return uid


class OrderedList(list):
    def append(self, *args):
        key = args[0]
        for index, (k, _) in enumerate(self):
            if k > key:
                self.insert(index, args)
                break
        else:
            list.append(self, args)


class BasePlugin(object):
    HEADER = 100

    def __init__(self, uid=None):
        self.tasks = OrderedList()
        self.channels = set()
        self.channels.add('net')
        self.sent = dict()
        self._thread = None
        self.running = False
        self.uid = uid or genuid()

    def send(self, addr=None, **msg):
        # msg.setdefault(SENDER_ID, self.uid)
        # msg.setdefault(MSG_ID, genuid())
        # msg.setdefault(RESPONSE_ID, 0)
        msg[SENDER_ID] = self.uid
        msg[MSG_ID] = genuid()

        self.sent[msg[MSG_ID]] = time() + SEND_TIMEOUT

        raw = self.pack(msg)
        self._send(raw, addr)

    def _send(self, raw, addr):
        raise NotImplementedError()

    def _purge_timedout(self):
        "Remove all timedout references of sent messages"
        now = time()
        for k, timeout in self.send.items():
            if timeout < now:
                self.send.pop(k)

    def pack(self, data):
        return encode(data)

    def unpack(self, raw):
        return decode(raw)

    def start(self, threaded=True):
        if threaded:
            self._thread = threading.Thread(target = self._start)
            self._thread.start()
        else:
            self._start()

    def stop(self, wait=True):
        self.running = False

    def answer(self, msg):
        answer = Message(msg.get('_msg', msg))
        answer[RESPONSE_ID] = answer[MSG_ID]
        # answer[SENDER_ID] = self.uid  # already done in send()
        answer.pop('_msg', None)
        return answer

    def do_ping(self, uid, mid, addr, **msg):
        log.info('Request: %s', msg)
        answer = self.answer(msg)
        log.info('Answer: %s', answer)
        return answer

    def response_ping(self, uid, mid, addr, **msg):
        log.info('Reponse from: %s: %s, %s', uid, addr, msg)

DEFAULT_ADDRESS = ('', 20000)
BROADCAST = ('<broadcast>', DEFAULT_ADDRESS[1])

class Plugin(BasePlugin):
    def __init__(self, uid=None, address=None):
        BasePlugin.__init__(self, uid)
        address = address or DEFAULT_ADDRESS
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.SOL_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.addr = address
        self.sock.bind(self.addr)

    def _send(self, raw, addr):
        # log.debug('%s %s (%s bytes)', uid, addr, len(raw))
        addr = addr or self.addr
        addr = BROADCAST
        self.sock.sendto(raw, addr)

    def _start(self):
        """Main loop.
        Attend RX messages, task queue and outgoin messages in a single loop.
        Try do keep all in a single function for speed.
        """
        sock = self.sock
        rlist = [sock]
        remain = 0  # always enters for 1st time
        queue = self.tasks

        log.info('Enter main loop')
        self.running = True

        while self.running:
            if queue:
                t0, task, task_addr = queue.pop(0)
                remain = max(0, t0 - time())
            else:
                remain = 0.25
                task = None

            # attend incoming messages
            # waiting until task timeout
            r, _, _ = select.select(rlist, [], [], remain)
            if r:
                # TODO: study if we store addr
                # TODO: for reply to this address.
                raw, addr = sock.recvfrom(0x4000)
                data = self.unpack(raw)
                data['addr'] = addr
                response = self.dispatch(data)

                # process response
                if isinstance(response, Message):
                    self.send(**response)  # addr in included in response
                elif isinstance(response, types.GeneratorType):
                    queue.append(0, response)
                # ignore any other response type

            # attend queued tasks
            if task:
                try:
                    response = task.next()
                except StopIteration:
                    pass
                except Exception, why:
                    pass

                # process response
                if isinstance(response, Message):
                    raw = self.pack(response)
                    self._send(raw, task_addr)
                elif isinstance(response, types.GeneratorType):
                    # nested generators
                    queue.append(0, response)
                else:  # must be the delay for next step
                    t0 += response
                    queue.append(t0, response)

        log.info('Exit main loop')

    def dispatch(self, msg):
        channel = msg[CHANNEL]
        if channel not in self.channels:
            return

        if msg[MSG_ID] in self.sent:
            return  # is an already processed message or a message that I've sent

        command = msg[COMMAND]

        response = msg.get(RESPONSE_ID, None)
        if response:
            timeout = self.sent.pop(response, None)
            if timeout:
                func = getattr(self, 'response_%s' % command, None)
            else:
                # I don't sent this message or response timeout
                func = None
        else:
            # is a request
            func = getattr(self, 'do_%s' % command, None)
        if func:
            return func(_msg=msg, **msg)


