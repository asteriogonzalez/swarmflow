import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import time
from random import randint
import hashlib

from plugin import Plugin, Message, Ping, PURGE_SENT_MSG, \
     BODY, CHANNEL, COMMAND, \
     DummyPlugin

class NonExistingService(Message):
    def __init__(self, **kw):
        dict.__init__(self, **kw)
        self[CHANNEL] = '<non-existing-channel>'
        self[COMMAND] = '<non-existing-command>'


class TestPlugin(Plugin):
    def __init__(self, *args, **kw):
        Plugin.__init__(self, *args, **kw)
        self.channels.add('test')
        self.ok = False

def test_startup():

    class A(TestPlugin):
        def response_ping(self, **msg):
            self.ok = True

    class B(TestPlugin):
        def do_ping(self, **msg):
            self.ok = True
            return Plugin.do_ping(self, **msg)

    p1 = A(uid='A')
    p2 = B(uid='B')

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

def test_timedout():
    p1 = TestPlugin()

    p1.start()

    while not (p1.running):
        time.sleep(0.1)

    msg = NonExistingService()
    p1.send(**msg)

    time.sleep(PURGE_SENT_MSG + 1)

    assert len(p1._context) == 0

    p1.stop()

    foo = 1

def test_dummy_plugin():

    service_list = []
    def services_callback(**answer):
        service_list.extend(answer[BODY])
        print "SERVICES:", service_list

    headers = []
    def headers_callback(**answer):
        headers.extend(answer[BODY])
        print "HEADERS:", headers

    p1 = DummyPlugin()
    p2 = DummyPlugin()

    p1.start()
    p2.start()

    while not (p1.running):
        time.sleep(0.1)

    msg = Message(
        command='services',
        channel='net',
        _callback=services_callback,
    )
    p1.send(**msg)

    for _ in range(10):
        if service_list:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError('timeout in %s' % msg[COMMAND])

    msg = Message(
        command='get_url_headers',
        body='https://lifehacker.com',
        channel='test',
        _callback=headers_callback,
    )
    p1.send(**msg)

    for _ in range(100):
        if headers:
            break
        time.sleep(0.1)
    else:
        raise RuntimeError('timeout in %s' % msg[COMMAND])

    p1.stop()
    p2.stop()

    foo = 1


if __name__ == '__main__':
    test_dummy_plugin()
    test_startup()
    test_timedout()
