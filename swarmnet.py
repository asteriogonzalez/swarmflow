import socket
import select

from udptl import UDPTL, Handler
from random import randint
import hashlib
import time
from collections import deque
from cPickle import dumps, loads
import ifcfg
from loggers import get_logger
from pprint import pprint

log = get_logger(__file__)


CMD_NEIGHBORS = 'neighbors'
CMD_PING = 'ping'
CMD_CALLBACK = 'callback'
CMD_CONNECT = 'connect'

PUNCH_ATTEMPS = 10

class Ring(Handler):
    def __init__(self, nid, transport, addr=None):
        uid = 'ring'
        Handler.__init__(self, uid, transport, addr)
        self.nid = nid
        self.known_nodes = dict()
        self._msg_counter = randint(0, 10**4)
        self.queue = deque()
        self._connects = dict()

    def dispatch(self, uid, msg, addr):
        # print uid, msg, addr
        if not msg['address']:
            msg['address'] = addr

        self.known_nodes[msg['address']] = msg['nid']
        # print "-" * 70
        # print "- Node: %s" % self.nid
        # for address, nid in self.known_nodes.items():
            # print address, nid

        log.debug(msg)
        func = getattr(self, 'do_%s' % msg['command'], None)
        if func:
            # TODO: include an automatic response
            func(uid, msg, addr)

        foo = 1

    def do_neighbors(self, uid, msg, addr):
        if msg['response']:
            body = msg['body']
            self.known_nodes.update(body)
            log.info("Neighbors of Node: %s", self.nid)
            for address, nid in self.known_nodes.items():
                log.info('%s : %s', address, nid)

        else:
            x0, cut = msg['body']
            x0 = int(x0, 16)
            distance = dict()
            for address, nid in self.known_nodes.items():
                d = abs(int(nid, 16) - x0)
                if d > 0:
                    distance[address] = d

            closer = distance.values()
            closer.sort()

            if closer:
                closer = closer[:cut][-1]
            else:
                closer = 0

            winners = [a for a in distance if distance[a] <= closer]
            winners = dict([(a, self.known_nodes[a]) for a in winners])

            self.answer(msg, addr, winners)

    def do_callback(self, uid, msg, addr):
        """
        - A send connect S
        - S send connect A, B
        - A start to send pings to B
        - B start to send pings to A
        """
        if msg['response']:
            pass
        else:
            a_nid = msg['nid']
            b_nid = msg['body']
            a_address = addr
            b_address = self.known_nodes.get(b_nid)
            if b_address:
                a_callback = self.new_message(CMD_CONNECT, (b_nid, b_address))
                b_callback = self.new_message(CMD_CONNECT, (a_nid, a_address))
                self.send(a_callback, a_address)
                self.send(b_callback, b_address)

    def do_connect(self, uid, msg, addr):
        if msg['response']:
            pass
        else:
            b_nid, b_address = msg['body']
            self.known_nodes[b_address] = b_nid
            log.info('Start Punching node %s at %s', b_nid, b_address)
            self._connects[b_address] = PUNCH_ATTEMPS

    def do_ping(self, uid, msg, addr):
        if msg['response']:
            pass
        else:
            self.answer(msg, addr)

    def next_response(self):
        # print "next_response"
        if len(self.queue) > 0:
            return self.queue.popleft()

    def idle(self):
        for address, attemps in self._connects.items():
            ping = self.new_message(CMD_PING)
            log.info('Trying to punch: %s', address)
            self.send(ping, address)
            if attemps > 0:
                self._connects[address] -= 1
            else:
                self._connects.pop(address)

    def timer(self):
        for address in self.known_nodes:
            self.ask_neighbors(address)

    def add_node(self, address):
        self.known_nodes[address] = None

    def ask_neighbors(self, address):
        log.info('Asking to: %s', address)
        msg = self.new_message(CMD_NEIGHBORS, (self.nid, 8))
        self.send(msg, address)

    def send(self, msg, address):
        msg = dict(msg)
        self.queue.append((self.uid, msg, address))

    def answer(self, msg, address, body=''):
        res = dict(msg)
        res['nid'] = self.nid
        res['response'] = 1
        res['body'] = body
        res['address'] = None

        self.send(res, address)

    def new_message(self, command, body=''):
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



if __name__ == '__main__':
    pass

