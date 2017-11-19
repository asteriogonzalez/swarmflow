import os
from agent import *

# -----------------------------------------------------
# Agent that implement a FS spooler
# -----------------------------------------------------
def fileiter(top):
    for root, foldes, files in os.walk(top):
        for name in files:
            filename = os.path.join(root, name)
            yield filename


DEFAULT_ROOT = 'spooler'

def sort(data, orig):
    "Sort a list by hex distance to an origin"
    orig = int(orig, 16)
    def _sort(a, b):
        return cmp(abs(int(a, 16) - orig), abs(int(b, 16) - orig))

    data.sort(_sort)
    return data


class FSAgent(Agent):
    """Agent implementation that also use a FS spooler to comunicate
    with other agents.

    Layout:

    root/channel/<channel_name>/<req_hash>.req
    root/channel/<channel_name>/<req_hash>.res
    root/<uid>/<req_hash>.msg
    root/heartbeat/<uid>
    """

    SPOOLER = 'spooler'
    HEARTBEAT = 'heartbeat'
    DEAD_TIMEOUT = 900

    def __init__(self, uid=None, address=None, root=None):
        Agent.__init__(self, uid, address)
        self.root = root or DEFAULT_ROOT

    def _idle(self):
        Agent._idle(self)
        self._process_fs()

    def _process_fs(self):
        """Search for incomeing messages from FS.
        Matching messages in channels are sortered by uid distance.
        """
        # update heartbeat state
        heartbeat = os.path.join(self.root, self.HEARTBEAT)
        filename = os.path.join(heartbeat, self.uid)
        content = '%s' % time()
        self._push_file(filename, content)

        # dead and alive agents
        now = time()
        dead = list()
        alive = list()
        for filename in fileiter(heartbeat):
            try:
                beat = int(open(filename, 'r').read())
                if now - beat > self.DEAD_TIMEOUT:
                    dead.append(filename)
                else:
                    alive.append(filename)
            except Exception, why:
                print why

        # get direct messages

        # get channels messages
        inbox = []
        spooler = os.path.join(self.root, self.SPOOLER)
        for root, foldes, files in os.walk(spooler):
            existing = []
            if root in self.channels:
                sort(data, self.uid)


        # garbage collector for spooler
        # remove folder from dead agents
        # remove dead heartbeat files
        # remove non-used empty channels

    def _push_file(self, filename, content):
        """Dump content into a file, creating directories if not exits."""
        parent = os.path.dirname(filename)
        if not os.path.exists(parent):
            os.makedirs(parent)
        with open(filename, 'w') as fp:
            fp.write(content)












