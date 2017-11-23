import threading
import socket
import select
from baseagent import *

# -----------------------------------------------------
# iAgent using UDP sockets and Threading
# -----------------------------------------------------

DEFAULT_ADDRESS = ('', 20000)
BROADCAST_ADDR = (BROADCAST, DEFAULT_ADDRESS[1])


class Agent(iAgent):
    """iAgent implementation using select, sockets or fds.
    """

    def __init__(self, uid=None, address=None):
        iAgent.__init__(self, uid)

        address = address or DEFAULT_ADDRESS
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                                   socket.SOL_UDP)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.addr = address
        self._sock.bind(self.addr)

        self.channels = set()
        self.channels.add('net')
        self._thread = None

    def start(self, threaded=True):
        """Start the agent in threaded mode (default)"""
        if threaded:
            self.running = True
            self._thread = threading.Thread(target = self._main)
            self._thread.start()
        else:
            iAgent.start(self)

    def _send(self, raw, addr=None):
        """Sent a raw message to an address.
        If not address it will sent using broadcast.
        """
        # log.debug('%s %s (%s bytes)', uid, addr, len(raw))
        addr = addr or self.addr
        addr = BROADCAST_ADDR
        self._sock.sendto(raw, addr)

    def _wait(self, remain):
        """Wait for activity for a while.
        Using select over sockets.
        """
        r, _, _ = select.select([self._sock], [], [], remain)
        return r

    def _process(self, activity):
        """Try to get some incoming messages from activity info.
        activity could be a socket list, or any other handler
        that we can use here to get the messages.
        """
        # TODO: study if we store addr
        # TODO: for reply to this address.
        for sock in activity:
            raw, addr = sock.recvfrom(0x4000)
            msg = unpack(raw)
            if msg:
                msg[ADDRESS] = addr
                self.push(msg)

if __name__ == '__main__':

    print "-End-"
