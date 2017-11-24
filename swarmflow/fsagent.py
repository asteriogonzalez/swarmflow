import os
import re
from agent import *

# -----------------------------------------------------
# Agent that implement a FS spooler
# -----------------------------------------------------
def fileiter(top, regexp='.*', info=None):
    if isinstance(regexp, types.StringType):
        regexp = [regexp]

    _regex = []
    for r in regexp:
        if isinstance(r, types.StringTypes):
            r = re.compile(r, re.DOTALL | re.I | re.VERBOSE)
        _regex.append(r)

    for root, foldes, files in os.walk(top):
        for name in files:
            filename = os.path.join(root, name)
            for reg in _regex:
                m = reg.search(filename)
                if m:
                    if info == 'd':
                        yield filename, m.groupdict()
                    elif info == 'g':
                        yield filename, m.groups()
                    else:
                        yield filename
                    break


DEFAULT_ROOT = 'spooler'

def sort(data, orig):
    "Sort a list by hex distance to an origin"
    orig = int(orig, 16)
    def _sort(a, b):
        return cmp(abs(int(a, 16) - orig), abs(int(b, 16) - orig))

    data.sort(_sort)
    return data


def push_request(msg, root):
    mid = msg.setdefault(MSG_ID, genuid())
    content = pack(msg)
    # filename = hashlib.sha1(content).hexdigest() + '.req'
    filename = '%s.req' % mid
    filename = os.path.join(root, FSAgent.CHANNEL, msg[CHANNEL], filename)
    push_file(filename, content)



def push_file(filename,
              content):
    """Dump content into a file, creating directories if not exits."""
    parent = os.path.dirname(filename)
    if not os.path.exists(parent):
        os.makedirs(parent)
    with open(filename, 'w') as fp:
        fp.write(content)

READY = 0
PROCESSING = 1
DONE = 2


def mark_file(filename, uid, status):
    if status == PROCESSING:
        newname = re.sub(r'([a-z,0-9]{40}.\w+$)', r'%s.\1' % uid, filename)
    elif status == READY:
        newname = re.sub(r'([a-z,0-9]{40}.)([a-z,0-9]{40}).\w+$', r'\2', filename)
    elif status == DONE:
        newname = re.sub(r'([a-z,0-9]{40}.)([a-z,0-9]{40}).(req)$', r'\2.res', filename)

    os.renames(filename, newname)
    os.unlink(newname)  # just debug


class FSAgent(Agent):
    """Agent implementation that also use a FS spooler to comunicate
    with other agents.

    Layout:

    root/channel/<channel_name>/<req_hash>.req
    root/channel/<channel_name>/<req_hash>.res
    root/<uid>/<req_hash>.msg
    root/heartbeat/<uid>
    """

    CHANNEL = 'channel'
    HEARTBEAT = 'heartbeat'
    DEAD_TIMEOUT = 900



    def __init__(self, uid=None, address=None, root=None):
        Agent.__init__(self, uid, address)
        self.root = root or DEFAULT_ROOT
        self.spool = dict()

    def _idle(self):
        Agent._idle(self)
        self._process_fs()

    def _process_fs(self):
        """Search for incomeing messages from FS.
        Matching messages in channels are sortered by uid distance.
        """
        if not self.spool:
            self._set_spoolers()

        # update heartbeat state
        content = '%s' % time.time()
        push_file(self.spool['heartbeat_file'], content)

        # dead and alive agents
        now = time.time()
        dead = list()
        alive = list()
        for filename in fileiter(self.spool['heartbeat']):
            try:
                beat = float(open(filename, 'r').read())
                if now - beat > self.DEAD_TIMEOUT:
                    dead.append(filename)
                else:
                    alive.append(filename)
            except Exception, why:
                traceback.print_exc()
                print why

        # get direct messages

        # get channels messages
        inbox = []
        reg = r'%s/(%s)/%s' % (
            self.spool[self.CHANNEL],
            r'|'.join(self.channels),
            r'[a-z,0-9]{40}.req'
            )

        for filename in fileiter(self.root, reg):
            try:
                msg = unpack(open(filename, 'r').read())
                self.push(msg)
                mark_file(filename, self.uid, PROCESSING)
            except Exception, why:
                traceback.print_exc()
                print why


        # garbage collector for spooler
        # remove folder from dead agents
        # remove dead heartbeat files
        # remove non-used empty channels




    def _set_spoolers(self):
        """Create the spooler names for later fast access on."""
        sp = self.spool
        sp['heartbeat'] = heartbeat = os.path.join(self.root, self.HEARTBEAT)
        sp['heartbeat_file'] = filename = os.path.join(heartbeat, self.uid)
        sp['channel'] = channel = os.path.join(self.root, self.CHANNEL)

        for name in self.channels:
            path = os.path.join(channel, name)
            sp[name] = path














