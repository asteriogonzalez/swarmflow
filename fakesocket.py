from collections import namedtuple
import socket
from random import randint
import time
import ifcfg
from netaddr import IPAddress
# import ipaddress

# TODO: use cjon if is faster despite the tuple conversion
from cPickle import loads, dumps
import select


# TODO: use raw tuples if are faster
Message = namedtuple('Message', ['data', 'from_', 'to_'])

default = ifcfg.default_interface()

bc_addr = (default['broadcast'], randint(20100, 65000))
bc_addr = (default['broadcast'], 20100)

bc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# activate SO_BROADCAST
bc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# reusing same address means other process will be listening to same port
bc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

bc_sock.bind(bc_addr)

NEVER_EXPIRE = 0
ROUTE_EXPIRE = 300

WAN_address = None
def set_WAN_address(address=None):
    global WAN_address
    if not address:

        address = []
        for i in range(4):
            address.append(str(randint(1, 255)))
        address = '.'.join(address)

    WAN_address = address



class FakeSocket(object):
    _binded = dict()
    WAN_address = None

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0,
                         _sock=None):

        self.family = family
        self.type = type
        self.proto = proto
        self._sock = _sock

        self._queue = list()
        self._wan_address = None

    def bind(self, address):
        self._local_address = address
        # TODO: detect WAN / LAN address
        ip, port = address
        if ip and not IPAddress(ip).is_private():
            # self._wan_address = self._new_WAN_port()
            self._wan_address = address
            self._binded[self._wan_address] = [self, NEVER_EXPIRE]

    def sendto(self, data, address):
        self._update_keep_alive()
        if address:
            msg = Message(data, self._wan_address, address)
            raw = dumps(msg, 2)
            bc_sock.sendto(raw, bc_addr)

    def recvfrom(self, size):
        msg = self._queue.pop(0)
        return msg.data, msg.from_



    @classmethod
    def _new_WAN_port(cls):
        while True:
            port = randint(13000, 65000)
            address = (WAN_address, port)
            if address not in cls._binded:
                break
        return address

    def _update_keep_alive(self):
        if not self._wan_address:
            self._wan_address = self._new_WAN_port()

        info = self._binded.get(self._wan_address)
        if not info or info[-1] != NEVER_EXPIRE:
            self._binded[self._wan_address] = [self, time.time() + ROUTE_EXPIRE]

    def _check_keep_alive(self):
        info = self._binded.get(self._wan_address)
        if info:
            if time.time() > info[1]:
                self._binded.pop(self._wan_address)
                self._wan_address = None
            else:
                return True
        return False

    @classmethod
    def select(cls, rlist, wlist, xlist, timeout=None):
        for sock in rlist:
            if sock._queue:
                return [sock], [], []

        if timeout is None:
            timeout = 10 ** 10

        t1 = time.time() + timeout
        remain = t1 - time.time()
        while remain > 0:
            _rlist = []
            r, _, _ = select._select_([bc_sock], [], [], remain)
            # now = time.time()
            if r:
                raw, addr = bc_sock.recvfrom(0x4000)
                try:
                    msg = loads(raw)
                    info = cls._binded.get(msg.to_)
                    if info:
                        sock, expire = info
                        if expire == NEVER_EXPIRE or \
                           sock._check_keep_alive():
                            sock._queue.append(msg)
                            sock._update_keep_alive()
                            if sock in rlist:
                                _rlist = [sock]
                                break
                except Exception, why:
                    raise why

            remain = t1 - time.time()

        return _rlist, _, _


# ----------------------------------------------------------
# patch libraries
# ----------------------------------------------------------
socket._socket_ = socket.socket
select._select_ = select.select

socket.socket = FakeSocket
select.select = FakeSocket.select

def test_broadcast():
    import time
    import select
    i = random.randint(0, 1000)
    while True:
        n = random.randint(1, 5)
        r, _, _ = select.select([bc_sock], [], [], n)
        if r:
            raw, addr = bc_sock.recvfrom(0x4000)
            print addr, raw
        else:
            i += 1
            raw = 'Hello! %d' % i
            bc_sock.sendto(raw, bc_addr)

def test_fakesocket():
    s1 = socket.socket(type=socket.SOCK_STREAM)
    addr1 = ('', randint(30000, 60000))
    s1.bind(addr1)
    set_WAN_address()

    s2 = socket.socket(type=socket.SOCK_STREAM)
    addr2 = ('', randint(30000, 60000))
    s2.bind(addr2)
    set_WAN_address()

    VISIBLE_HOST = '94.177.253.187'
    s3 = socket.socket(type=socket.SOCK_STREAM)
    addr3 = (VISIBLE_HOST, randint(30000, 60000))
    s3.bind(addr3)

    i = randint(0, 1000)
    while True:
        n = randint(1, 5)
        r, _, _ = select.select([s1, s3], [], [], n)
        if r:
            raw, addr = r[0].recvfrom(0x4000)
            print "%s in %s from %s" % (raw, r[0]._wan_address, addr)
        else:
            i += 1
            raw = 'Hello! %d' % i
            s2.sendto(raw, s1._wan_address)  # not received
            #s1.sendto(raw, s3._wan_address)
            s2.sendto(raw, s3._wan_address)  # received (public WAN)


# -----------------------------------------------------------------
# Final setups
# -----------------------------------------------------------------
set_WAN_address()

if __name__ == '__main__':
    #test_broadcast()
    test_fakesocket()

