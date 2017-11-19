import time
from swarmflow.agent import Agent, expose, Ping, CALLBACK, MSG_ID

class TestPlugin(Agent):
    def __init__(self, *args, **kw):
        Agent.__init__(self, *args, **kw)
        # self.channels.add('test')  # TODO: review channels
        self.ok = False
        self.callback_result = None

    def callback_method(self, **msg):
        self.callback_result = msg

def test_ping_pong():
    """Test transport layer using ping / pong
    and test the callback feature as well.
    """

    class A(TestPlugin):
        @expose
        def pong(self, **kw):
            self.ok = True

    class B(TestPlugin):
        @expose
        def ping(self, **kw):
            self.ok = True
            return Agent.ping(self, **kw)

    p1 = A(uid='A')
    p2 = B(uid='B')

    p1.start()
    p2.start()

    while not (p1.running and p2.running):
        time.sleep(0.1)

    msg = Ping()
    msg[CALLBACK] = p1.callback_method
    p1.send(**msg)

    t0 = time.time()
    while not (p1.ok and p2.ok and p1.callback_result):
        time.sleep(0.1)
        if time.time() - t0 > 5:
            raise RuntimeError('Timeout waiting for Ping response')

    p1.stop()
    p2.stop()

    foo = 1
