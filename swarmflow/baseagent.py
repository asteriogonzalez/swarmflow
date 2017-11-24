import uuid
import hashlib
import time
import types
import sys
import traceback
# from zlib import compress, decompress
from cjson import encode, decode
from loggers import get_logger
# from loggers import flush
from collections import OrderedDict
from pprint import pprint

from swarmflow.utils import SQueue
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
RESPONSE_ID = 'rid'
SENDER_ID = 'uid'
BODY = 'body'
FIRE = 'fir'

ADDRESS = '_addr'
CALLBACK = '_callback'
TIMEOUT = '_timeout'
FULL_MSG = '_msg'
FUNC = '_func'

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

class Timeout(Message):
    def __init__(self, *args, **kw):
        kw[FIRE] = time.time() + SEND_TIMEOUT

        kw[COMMAND] = ''
        kw.setdefault(MSG_ID, genuid())
        Message.__init__(self, *args, **kw)


class Ping(Message):
    CMD = 'ping'

    def __init__(self, *args, **kw):
        Message.__init__(self, *args, **kw)
        self[CHANNEL] = CHANNEL_NET
        self[COMMAND] = self.CMD


# -----------------------------------------------------
# Special Time Sorted Queue
# -----------------------------------------------------
MAX_SLEEP = 0.25  # secs

def default__field_selector(msg):
    "messages are sorted by fire time"
    return msg.get(FIRE, 0)

def default_key_selector(msg):
    "messages are sorted by fire time"
    return msg.get(MSG_ID, 0)

class TQueue(SQueue):
    def __init__(self, *args, **kwds):
        SQueue.__init__(self,
            __field_selector__=default__field_selector,
            __key_selector__=default_key_selector
            )

    def lookup(self, last=True):
        if self:
            key, t0, msg = SQueue.getitem(self, last=True)
            return key, t0 - time.time(), msg
        return None, MAX_SLEEP, None

    def extract(self, last=True):
        if self:
            key, msg = SQueue.popitem(self, last=True)
            return key, msg
        return None, None


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

class ExecutionContext(object):
    """Contains the execution context for a task.
    """
    def __init__(self, request):
        self.request = request
        self.responses = list()



class iAgent(Exposable):
    """Interface for Generic Distributed Agents

    - Threading is not necessary in this hierarchy level.
    - Direct messages and Publisher/Subscripter pattern.
    - Hasn't implementation for transport layer.

    """
    # TODO: implement Publisher/Subscripter pattern at this level
    IDLE_CYCLE = max(20, PURGE_SENT_MSG)    # secs

    def __init__(self, uid=None):
        self.uid = uid or genuid()
        self._queue = TQueue()
        # self._queue = deque()
        self.running = False
        self._context = dict()  # already sent messages
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
        mid = msg[MSG_ID] = genuid()
        addr = msg.get(ADDRESS)

        if not msg.get(RESPONSE_ID):  # is a request
            # check callback are iterables
            callback = msg.setdefault(CALLBACK, [])
            if not isinstance(callback, types.ListType):
                msg[CALLBACK] = [callback]
            # check timeout callbacks are iterables
            timeout = msg.setdefault(TIMEOUT, [])
            if not isinstance(timeout, types.ListType):
                msg[TIMEOUT] = [timeout]

            # timeout acts like a response but dealing with no answer scenario
            # always is fired but only have sense when we have not receive
            # anything from remote side or a while.
            t0 = Timeout()
            t0[RESPONSE_ID] = mid
            t0[FUNC] = self._request_timeout
            self._queue.push(t0)

            self._context[mid] = ExecutionContext(msg)

        raw = pack(msg)
        self._send(raw, addr)

    def answer(self, msg, klass=Message):
        """Create a response from a incoming message.
        """
        _msg = msg.get(FULL_MSG, msg)
        answer = klass(_msg)
        answer[RESPONSE_ID] = _msg[MSG_ID]
        # answer[SENDER_ID] = self.uid  # already done in send()
        answer.pop(FULL_MSG, None)
        answer.pop(COMMAND)
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

        if msg[MSG_ID] in self._context:
            # check if is an already processed message or
            # a message that I've sent
            # as a consecuence, an agent can't send messages to itself
            return

        req_id = msg.get(RESPONSE_ID)
        context = self._context.get(req_id)
        if context:
            # decidir como le damos vida a esta request
            # si es generador es sencillo
            # si era req aislada, solo callbacks son posibles
            context.responses.append(msg)  # TODO: use of context...?
            func = self._dispatch_response
        else:
            # add message info queue
            msg.setdefault(FIRE, 0)
            func = self._exposed_.get(msg.get(COMMAND))

        if func:
            assert not msg.get(FUNC)
            msg[FUNC] = func
            self._queue.push(msg)

    def _main(self):
        "main loop"
        queue = self._queue
        next_idle = 0
        while self.running:
            # get remaining time until next task
            _, remain, _ = self._queue.lookup()

            # wait for incoming messages
            activity = self._wait(remain)
            if activity:
                self._process(activity)

            # handle the next message (if any)
            mid, remain, msg = self._queue.lookup()
            if remain <= 0:
                self._queue.pop(mid)
                self._handle(msg)
            else:
                foo = 1

            if not activity:
                now = time.time()
                if now > next_idle:  # performs idle tasks
                    self._idle()
                    next_idle = now + self.IDLE_CYCLE

    def _wait(self, remain):
        """Wait for activity for a while.
        Usually returns the control to pseudo-thread hub (e.g. evenlet)
        or make a select over some sockets.
        """
        print "%s waiting %s" % (self.uid, remain)
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
        # self._purge_timedout()
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

        func = msg[FUNC]  # must be already set in push or by user
        if func.func_code.co_flags & 0x20:
            try:
                response = func.next()
            except StopIteration:
                pass
            except Exception, why:
                pass
        else:
            response = self._dispatch(func, msg)

        # process response
        if isinstance(response, types.GeneratorType):
            assert "Think if put generator on queue, and use push()"
            # self._queue.append(msg)
            return

        if isinstance(response, Message):
            self.send(**response)  # addr in included in response
        else:
            # its just a value, then convert into message before sending
            # TODO: distinguish between return None and return nothing
            response = self._wrap(response, msg)
            if response:
                self.send(**response)

        # the method is exhasuted, process with callbacks if any
        for callback in msg.get(CALLBACK, []):
            self._dispatch(callback, msg)

    def _dispatch(self, func, msg):
        "Call func mapping arguments"
        if not func:
            return

        # bounded function or not
        if isinstance(func, types.FunctionType):
            args = (self, )
        else:
            args = tuple()

        # matched args names
        kw = dict()
        if func.func_code.co_flags & 0x08:
            kw[FULL_MSG] = msg  # special call bindings

        for name in func.func_code.co_varnames:
            if name in msg:
                kw[name] = msg[name]

        # execute function
        try:
            return func(*args, **kw)
        except Exception, why:
            traceback.print_exc()
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
            answer.pop(COMMAND, None)
            answer[BODY] = value
            return answer

    def _purge_timedout(self):
        "Remove all timedout references of sent messages"
        # now = time.time()
        # for k, info in self._context.items():
            # if info[0] < now:  # info[0] is timeout
                # log.info('PURGE msg: %s', k)
                # self._context.pop(k)


    def _dispatch_response(self, **msg):
        res = msg[FULL_MSG]
        context = self._context.pop(res[RESPONSE_ID])
        req = context.request
        for callback in req[CALLBACK]:
            self._dispatch(callback, res)


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
        answer = self.answer(msg)
        log.info('Answer: %s', answer)
        return answer

    @expose
    def pong(self, **msg):
        log.info('Response: %s', msg)

    def _request_timeout(self, rid, **kw):
        context = self._context.pop(rid, None)
        if context:
            req = context.request
            for callbask in req[TIMEOUT]:
                self._dispatch(callbask, req)
        else:
            print "timeout not necessary"
