import uuid
import hashlib
from collections import namedtuple

from swarmflow.exposable import Exposable, expose

def genuid():
    uid = hashlib.sha1(uuid.uuid1().get_hex()).hexdigest()
    return uid

_Call = namedtuple('Call', ['method', 'args', 'kw'])


def Call(method, *args, **kw):
    return _Call(method, args, kw)





class Agent(Exposable):
    """Interface for Generic Distributed Agents

    - Threading is not necessary in this hierarchy level.
    - Direct messages and Publiher/Subscripter pattern.
    - Hasn't implementation for transport layer.

    """

    def __init__(self, uid=None):
        self.uid = uid  # or genuid()
        # self.tasks = OrderedList(
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def dispatch(self, call):
        func = self._exposed_[call.method]
        # func.func_defaults
        # kw = dict(call.kw)
        # call_kw = dict()
        # call_args = list()
        # varnames = func.func_code.co_varnames
        # for k in kw:
            # if k in varnames:
                # call_kw[k] = kw.pop(k)

        return func(self, *call.args, **call.kw)

    @expose(a=1)
    def dir(self):
        print "dir"

    @expose
    def foo(self, a, b=1):
        print "inside foo"


if __name__ == '__main__':

    a = Agent(uid=1)

    c = Call('foo', 2, b=7)

    a.dispatch(c)

    print "-End-"
