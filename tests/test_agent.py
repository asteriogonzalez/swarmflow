import time
import operator
import inspect
import random

from swarmflow.baseagent import *
from swarmflow.agent import Agent, Ping
from swarmflow.fsagent import FSAgent

CHANNEL_TEST = 'testing'

def wait_ready(*args):
    t0 = time.time()
    while not reduce(operator.and_, [a.running for a in args]):
        time.sleep(0.1)
        if time.time() - t0 > 5:
            raise RuntimeError('Timeout waiting for Agents to be running')


def wait_until(condition, context=None, timeout=5):
    if context is None:
        frame = inspect.currentframe()
        context = frame.f_back.f_locals

    t0 = time.time()
    while not eval(condition, globals(), context):
        time.sleep(0.1)
        if time.time() - t0 > timeout:
            raise RuntimeError('Timeout waiting for %s' % condition)

    foo = 1

class TestPlugin(Agent):
    def __init__(self, *args, **kw):
        Agent.__init__(self, *args, **kw)
        self.channels.add(CHANNEL_TEST)  # TODO: review channels
        self.ok = False
        self.callback_result = None
        self.timeout = False

    def callback_method(self, **msg):
        self.callback_result = msg

    def timeout_func(self, **msg):
        self.timeout = True

    def check_eval(self, body, **msg):
        assert int(body) == 13
        self.ok = True

    @expose
    def eval(self, body, **kw):
        "return the evaluation of the expression contained in body"
        return eval(body)


class A(TestPlugin):
    @expose
    def pong(self, **kw):
        self.ok = True


class B(TestPlugin):
    @expose
    def ping(self, **kw):
        self.ok = True
        return Agent.ping(self, **kw)


def random_text(n=5):
    return ''.join([chr(random.randint(92, 122)) for _ in range(n)])


def random_message(**kw):
    msg = Message(**kw)
    msg.setdefault(SENDER_ID, genuid())
    msg.setdefault(CHANNEL, 'test_' + random_text())
    msg.setdefault(COMMAND, 'non_existing_' + random_text())
    return msg


# -----------------------------------------------------
# Agent tests
# -----------------------------------------------------
def test_timeout():
    "Test timeout feature"
    p1 = A(uid='A')
    p1.start()
    wait_ready(p1)

    msg = random_message()
    msg[TIMEOUT] = p1.timeout_func
    p1.send(**msg)
    wait_until('p1.timeout', timeout=SEND_TIMEOUT + 1)

    p1.stop()


def test_ping_pong():
    """Test transport layer using ping / pong
    and test the callback feature as well.
    """
    p1 = A(uid='A')
    p2 = B(uid='B')

    p1.start()
    p2.start()

    msg = Ping()
    msg[TIMEOUT] = p1.timeout_func
    msg[CALLBACK] = p1.pong
    p1.send(**msg)

    # TODO: review, maybe this assetion may fail is main thread are slow
    assert p1._context        # sent queue is not empty

    wait_until('p1.ok and p2.ok')
    assert not p1.timeout  # timeout has not been fired
    assert not p1._context    # sent queue is empty

    p1.stop()
    p2.stop()

def test_remote_eval_with_callbacks():
    """Test client-server architecure with a remote calculator.
    """
    p1 = A(uid='A')
    p2 = B(uid='B')

    p1.start()
    p2.start()

    msg = Message()
    msg[BODY] = '6 + 7'
    msg[COMMAND] = 'eval'
    msg[CHANNEL] = CHANNEL_TEST
    msg[CALLBACK] = p1.check_eval
    p1.send(**msg)

    # TODO: review, maybe this assetion may fail is main thread are slow
    assert p1._context        # sent queue is not empty

    wait_until('p1.ok')
    assert not p1.timeout  # timeout has not been fired
    assert not p1._context    # sent queue is empty

    p1.stop()
    p2.stop()

    wait_until('not(p1._thread.isAlive() and p2._thread.isAlive())')

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

    p1.stop()
    foo = 1

def test_ping_pong_broadcast_fs():
    pass


if __name__ == '__main__':
    # test_remote_eval_with_callbacks()
    test_timeout()
