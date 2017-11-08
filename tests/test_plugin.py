import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import time
from random import randint
import hashlib


from plugin import Plugin, Message, Ping

class TestPlugin(Plugin):
    def __init__(self, *args, **kw):
        Plugin.__init__(self, *args, **kw)
        self.ok = False

def test_startup():

    class A(TestPlugin):
        def response_ping(self, **msg):
            self.ok = True

    class B(TestPlugin):
        def do_ping(self, **msg):
            self.ok = True
            return Plugin.do_ping(self, **msg)

    p1 = A()
    p2 = B()

    p1.start()
    p2.start()

    while not (p1.running and p2.running):
        time.sleep(0.1)

    msg = Ping()
    p1.send(**msg)

    t0 = time.time()
    while not (p1.ok and p2.ok):
        time.sleep(0.1)
        if time.time() - t0 > 2:
            raise RuntimeError('Timeout waiting for Ping response')

    p1.stop()
    p2.stop()

    foo = 1


if __name__ == '__main__':
    test_startup()

