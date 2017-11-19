import uuid
import hashlib
from time import time, sleep
import types
from collections import namedtuple, deque
import socket
import select
from cjson import encode, decode
from loggers import get_logger
# from loggers import flush

from swarmflow.exposable import Exposable, expose

log = get_logger(__file__)


def genuid():
    "generate a new uid"
    uid = hashlib.sha1(uuid.uuid1().get_hex()).hexdigest()
    return uid

_Call = namedtuple('Call', ['method', 'args', 'kw'])


def Call(method, *args, **kw):
    return _Call(method, args, kw)

# -----------------------------------------------------
# Direct Messages and Publisher / Subscripter patterns
# -----------------------------------------------------


CHANNEL = 'channel'
COMMAND = 'cmd'
MSG_ID = 'mid'
RESPONSE_ID = 'response'
SENDER_ID = 'uid'
BODY = 'body'
CALLBACK = '_callback'
FULL_MSG = '_msg'


class Message(dict):
    """Plugin messages are simply dictionaries.
    message id
    response flag
    sender id
    channel
    body
"""
    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)

CHANNEL_NET = 'net'  # TODO: review


class Ping(Message):
    CMD = 'ping'
    def __init__(self, *args, **kw):
        Message.__init__(self, *args, **kw)
        self[CHANNEL] = CHANNEL_NET
        self[COMMAND] = self.CMD

class Pong(Message):
    CMD = 'pong'
    def __init__(self, *args, **kw):
        Message.__init__(self, *args, **kw)
        self[CHANNEL] = CHANNEL_NET
        self[COMMAND] = self.CMD



# -----------------------------------------------------
# Agent Interface
# -----------------------------------------------------
SEND_TIMEOUT = 1
PURGE_SENT_MSG = 4 + SEND_TIMEOUT


def pack(data):
    msg = dict((k, v) for (k, v) in data.items() if k[0] != '_')
    return encode(msg)


def unpack(raw):
    return decode(raw)


class iAgent(Exposable):
    """Interface for Generic Distributed Agents

    - Threading is not necessary in this hierarchy level.
    - Direct messages and Publisher/Subscripter pattern.
    - Hasn't implementation for transport layer.

    """
    # TODO: implement Publisher/Subscripter pattern at this level
    MAX_SLEEP = 0.25  # secs
    IDLE_CYCLE = max(20, PURGE_SENT_MSG)    # secs

    def __init__(self, uid=None):
        self.uid = uid or genuid()
        self._queue = deque()
        self.running = False
        self._sent = dict()  # already sent messages

    def start(self):
        self.running = True
        self._main()

    def stop(self):
        self.running = False

    def send(self, addr=None, **msg):
        # msg.setdefault(SENDER_ID, self.uid)
        # msg.setdefault(MSG_ID, genuid())
        # msg.setdefault(RESPONSE_ID, 0)
        msg[SENDER_ID] = self.uid
        msg[MSG_ID] = genuid()

        callback = msg.get(CALLBACK, [])
        if not isinstance(callback, types.ListType):
            callback = [callback]

        self._sent[msg[MSG_ID]] = (time() + SEND_TIMEOUT, callback)

        raw = pack(msg)
        self._send(raw, addr)

    def answer(self, msg, klass=Message):
        """Create a response from a incoming message.
        """
        answer = klass(msg.get(FULL_MSG, msg))
        answer[RESPONSE_ID] = answer[MSG_ID]
        # answer[SENDER_ID] = self.uid  # already done in send()
        answer.pop(FULL_MSG, None)
        return answer

    def push(self, msg):
        """Add a task into the process queue.
        Parameters are:
        - schedule time
        - task
        - sender address or location
        """
        # TODO: implement having in mind sender address, message and task
        # TODO: (unify all of them?, even the schedule time?)
        # channel = msg[CHANNEL]
        # if channel not in self.channels:
            # return

        if msg[MSG_ID] in self._sent:
            return  # is an already processed message or a message that I've sent

        command = msg[COMMAND]

        response = msg.get(RESPONSE_ID, None)
        if response:
            info = self._sent.pop(response, None)
            if info:
                for callback in info[1]:
                    callback(**msg)

        self._queue.append((0, msg, None))

    def _main(self):
        "main loop"
        queue = self._queue
        next_idle = 0
        while self.running:
            # get remaining time until next task
            if queue:
                # TODO: sender_addr must be inside task
                t0, task, sender_addr = queue.popleft()
                remain = max(0, t0 - time())
            else:
                remain = self.MAX_SLEEP
                task = None

            # wait for incoming messages
            activity = self._wait(remain)
            if activity:
                self._process(activity)

            # handle the message
            self._handle(task)

            if not activity:
                now = time()
                if now > next_idle:  # performs idle tasks
                    self._idle()
                    next_idle = now + self.IDLE_CYCLE

    def _wait(self, remain):
        """Wait for activity for a while.
        Usually returns the control to pseudo-thread hub (e.g. evenlet)
        or make a select over some sockets.
        """
        sleep(remain)  # dummy implementation just for testing

    def _process(self, activity):
        """Try to get some incoming messages from activity info.
        activity could be a socket list, or any other handler
        that we can use here to get the messages.
        """

    def _idle(self):
        """Performs any garbage of low priority tasks.
        Its called from time to time when there's not incoming activity.
        """
        self._purge_timedout()
        # ...

    def _handle(self, task):
        """Handle the task call.
        You can implement:

        1. direct calls and return value
        2. dialog between 2 agents using send() and next() generators
        3. any other paradigm.
        """
        if not task:
            return

        response = self._dispatch(task)

        # process response
        if isinstance(response, Message):
            self.send(**response)  # addr in included in response
        elif isinstance(response, types.GeneratorType):
            # TODO: review message unification
            self._queue.append((0, response, task.sender_addr))
        else:
            # its just a value, then convert into message before sending
            response = self._wrap(response, task)
            if response:
                self.send(**response)

    def _dispatch(self, task):
        func = self._exposed_[task[COMMAND]]
        # func.func_defaults
        # kw = dict(task.kw)
        # call_kw = dict()
        # call_args = list()
        # varnames = func.func_code.co_varnames
        # for k in kw:
            # if k in varnames:
                # call_kw[k] = kw.pop(k)

        kw = dict()
        kw[FULL_MSG] = task  # special call bindings
        for name in func.func_code.co_varnames:
            if name in task:
                kw[name] = task[name]

        return func(self, **kw)

    def _send(self, raw, addr):
        """Real send a message through the transport layer.
        message contains all the info needed to deliver physically
        the payload to the receiver.
        """
        raise NotImplementedError('implement using any Transport Layer')

    def _wrap(self, value, task):
        """Convert a value into a reply-to message to task sender."""
        if value is not None:
            answer = Message(task)
            answer[RESPONSE_ID] = answer[MSG_ID]
            # answer[SENDER_ID] = self.uid  # already done in send()
            answer.pop(FULL_MSG, None)
            answer[BODY] = value
            return answer

    def _purge_timedout(self):
        "Remove all timedout references of sent messages"
        now = time()
        for k, info in self._sent.items():
            if info[0] < now:  # info[0] is timeout
                log.info('PURGE msg: %s', k)
                self._sent.pop(k)

    @expose(help='return the list of exposed methods')
    def dir(self):
        result = dict()
        for name, method in self._exposed_.items():
            meta = method.__meta__
            # TODO: include calling arguments
            result[name] = dict(help=meta.get('help', ''))
        return result

    @expose
    def ping(self, **msg):
        log.info('Request: %s', msg)
        answer = self.answer(msg, Pong)
        log.info('Answer: %s', answer)
        return answer

    @expose
    def pong(self, **msg):
        log.info('Response: %s', msg)


