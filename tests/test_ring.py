import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import time
from random import randint
import hashlib

import fakesocket

from swarmnet import Ring
from udptl import UDPTL, Handler
from netaddr import IPNetwork


def test_ring():
    nodes = dict()
    N = 20
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
        time.sleep(randint(1, 4))

        nid = hashlib.sha1('node%d' % i).hexdigest()
        ring = Ring(nid, node)
        if i > 0:
            ring.add_node(KNOWN_ADDRESS)

        nodes[nid] = node
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

