import time
import operator
import inspect
from swarmflow.agent import Agent, expose, Ping, CALLBACK, MSG_ID
from swarmflow.fsagent import FSAgent

def wait_ready(*args):
    t0 = time.time()
    while not reduce(operator.and_, [a.running for a in args]):
        time.sleep(0.1)
        if time.time() - t0 > 5:
            raise RuntimeError('Timeout waiting for Agents to be running')


def wait_until(condition, context=None):
    if context is None:
        frame = inspect.currentframe()
        context = frame.f_back.f_locals

    t0 = time.time()
    while not eval(condition, globals(), context):
        time.sleep(0.1)
        if time.time() - t0 > 5:
            raise RuntimeError('Timeout waiting for Agents to be running')

    foo = 1

class TestPlugin(Agent):
    def __init__(self, *args, **kw):
        Agent.__init__(self, *args, **kw)
        # self.channels.add('test')  # TODO: review channels
        self.ok = False
        self.callback_result = None

    def callback_method(self, **msg):
        self.callback_result = msg


class A(TestPlugin):
    @expose
    def pong(self, **kw):
        self.ok = True


class B(TestPlugin):
    @expose
    def ping(self, **kw):
        self.ok = True
        return Agent.ping(self, **kw)


# -----------------------------------------------------
# Agent tests
# -----------------------------------------------------
def test_ping_pong():
    """Test transport layer using ping / pong
    and test the callback feature as well.
    """
    p1 = A(uid='A')
    p2 = B(uid='B')

    p1.start()
    p2.start()

    wait_ready(p1, p2)

    msg = Ping()
    msg[CALLBACK] = p1.callback_method
    p1.send(**msg)

    t0 = time.time()
    wait_until('p1.ok and p2.ok and p1.callback_result')

    p1.stop()
    p2.stop()

    foo = 1

def test_ping_pong_broadcast():
    pass

# -----------------------------------------------------
# Agent tests
# -----------------------------------------------------
def test_ping_pong_fs():
    p1 = FSAgent()
    p1.start()

    wait_ready(p1)
    time.sleep(10)

    p1.stop()
    foo = 1

def test_ping_pong_broadcast_fs():
    pass


