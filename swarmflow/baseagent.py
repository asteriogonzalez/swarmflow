import uuid
import hashlib
from time import time, sleep
import types
# from zlib import compress, decompress
from cjson import encode, decode
from loggers import get_logger
# from loggers import flush

from swarmflow.exposable import Exposable, expose

log = get_logger(__file__)

BROADCAST = '<broadcast>'

def genuid():
    "generate a new uid"
    uid = hashlib.sha1(uuid.uuid1().get_hex()).hexdigest()
    return uid


# -----------------------------------------------------
# Direct Messages and Publisher / Subscripter patterns
# -----------------------------------------------------


CHANNEL = 'chn'
COMMAND = 'cmd'
MSG_ID = 'mid'
RESPONSE_ID = 'response'
SENDER_ID = 'uid'
BODY = 'body'
FIRE = 'fir'

ADDRESS = '_addr'
CALLBACK = '_callback'
FULL_MSG = '_msg'

CHANNEL_NET = 'net'


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


def pack(msg):
    msg = dict((k, v) for (k, v) in msg.items() if k[0] != '_')
    # return compress(encode(msg))
    return encode(msg)


def unpack(raw):
    # return decode(decompress(raw))
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
        self._queue = list()
        # self._queue = deque()
        self.running = False
        self._sent = dict()  # already sent messages
        self.channels = set()
        self.channels.add(CHANNEL_NET)

    def start(self):
        self.running = True
        self._main()

    def stop(self):
        self.running = False

    def send(self, **msg):
        # msg.setdefault(SENDER_ID, self.uid)
        # msg.setdefault(MSG_ID, genuid())
        # msg.setdefault(RESPONSE_ID, 0)
        msg[SENDER_ID] = self.uid
        msg[MSG_ID] = genuid()
        addr = msg.get(ADDRESS)

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
        if msg[CHANNEL] not in self.channels:
            return

        if msg[MSG_ID] in self._sent:
            return  # an already processed message or a message that I've sent

        response = msg.get(RESPONSE_ID, None)
        if response:
            info = self._sent.pop(response, None)
            if info:
                for callback in info[1]:
                    callback(**msg)

        # add message info queue
        t0 = msg.setdefault(FIRE, 0)
        for idx, ext in enumerate(self._queue):
            if t0 < ext[FIRE]:
                self._queue.insert(idx, msg)
                break
        else:
            self._queue.append(msg)

    def _main(self):
        "main loop"
        queue = self._queue
        next_idle = 0
        while self.running:
            # get remaining time until next task
            if queue:
                msg = queue.pop()
                remain = max(0, msg[FIRE] - time())
            else:
                remain = self.MAX_SLEEP
                msg = None

            # wait for incoming messages
            activity = self._wait(remain)
            if activity:
                self._process(activity)

            # handle the message
            self._handle(msg)

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

    def _handle(self, msg):
        """Handle the msg.
        You can implement:

        1. direct calls and return value
        2. dialog between 2 agents using send() and next() generators
        3. any other paradigm.
        """
        if not msg:
            return

        response = self._dispatch(msg)

        # process response
        if isinstance(response, Message):
            self.send(**response)  # addr in included in response
        elif isinstance(response, types.GeneratorType):
            self._queue.append(msg)
        else:
            # its just a value, then convert into message before sending
            response = self._wrap(response, msg)
            if response:
                self.send(**response)

    def _dispatch(self, msg):
        func = self._exposed_.get(msg[COMMAND])
        if not func:
            return
        kw = dict()
        kw[FULL_MSG] = msg  # special call bindings
        for name in func.func_code.co_varnames:
            if name in msg:
                kw[name] = msg[name]

        try:
            return func(self, **kw)
        except Exception, why:
            print why



    def _send(self, raw, addr):
        """Real send a message through the transport layer.
        message contains all the info needed to deliver physically
        the payload to the receiver.
        """
        raise NotImplementedError('implement using any Transport Layer')

    def _wrap(self, value, msg):
        """Convert a value into a reply-to message to msg sender."""
        if value is not None:
            answer = Message(msg)
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
