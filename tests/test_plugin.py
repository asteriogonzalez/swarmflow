import sys
from os import path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
import time
from random import randint
import hashlib


from plugin import Plugin, Message, Ping

def test_startup():
    p1 = Plugin(uid='A')
    p2 = Plugin(uid='B')

    p1.start()
    p2.start()

    while not (p1.running and p2.running):
        time.sleep(0.1)

    msg = Ping()
    p1.send(**msg)

    time.sleep(3000)

    p1.stop()
    p2.stop()

    foo = 1


if __name__ == '__main__':
    test_startup()

