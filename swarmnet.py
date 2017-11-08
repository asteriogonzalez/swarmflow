import socket
import select

import fakesocket
from udptl import UDPTL, Handler
from random import randint
import hashlib
import time
from collections import deque
from cPickle import dumps, loads
from netaddr import IPAddress, IPNetwork, IPRange

CMD_NEIGHBORS = 'neighbors'
class Ring(Handler):
    def __init__(self, nid, transport, addr=None):
        uid = 'ring'
        Handler.__init__(self, uid, transport, addr)
        self.nid = nid
        self.known_nodes = dict()
        self._msg_counter = randint(0, 10**4)
        self.queue = deque()

    def dispatch(self, uid, data, addr):
        print uid, data, addr
        if not data['address']:
            data['address'] = addr

        self.known_nodes[data['address']] = data['nid']

    def next_response(self):
        # print "next_response"
        if len(self.queue) > 0:
            return self.queue.popleft()

    def idle(self):
        pass

    def timer(self):
        for address in self.known_nodes:
            self.ask_neighbors(address)

    def add_node(self, address):
        self.known_nodes[address] = None

    def ask_neighbors(self, address):
        msg = self._new_message(CMD_NEIGHBORS, 8)
        self.send(msg, address)

    def send(self, msg, address):
        msg = dict(msg)
        self.queue.append((self.uid, msg, address))

    def _new_message(self, command, body):
        self._msg_counter += 1
        rid = hashlib.sha1('%d%s%s' % (self._msg_counter,
                               time.time(),
                               randint(0, 10000))).hexdigest()

        msg = dict(
            nid=self.nid,
            command=command,
            rid=rid,
            response=0,
            jumps=0,
            address=None,
        )
        msg['body'] = body
        return msg



def test_ring():
    nodes = dict()
    N = 1
    port = randint(30000, 30000)

    KNOWN_NODE = '69.69.69.69'
    KNOWN_ADDRESS = (KNOWN_NODE, port)
    fakesocket.set_WAN_address(KNOWN_NODE)

    network = IPNetwork('10.0.0.0/8')
    for i, ip in enumerate(network):
        if i == 0:
            address = KNOWN_ADDRESS
        else:
            address = (ip.format(), port)


        print address
        node = UDPTL(address)
        node.start()

        nid = hashlib.sha1('node%d' % i).hexdigest()
        ring = Ring(nid, node)
        if i > 0:
            ring.add_node(KNOWN_ADDRESS)

        nodes[nid] = nid
        fakesocket.set_WAN_address()

        if i >= N:
            break


    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break



    for node in nodes.values():
        node.stop()

    foo = 1





if __name__ == '__main__':
    test_ring()

