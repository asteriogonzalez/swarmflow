import time
import random
from swarmflow.baseagent import Queue, Message, FIRE, MSG_ID, BODY, genuid

def random_messages(n=10):
    for _ in range(n):
        msg = Message()
        msg[FIRE] = random.randint(0, 10**6)
        msg[MSG_ID] = genuid()
        msg[BODY] = str('foo-%s' % random.randint(0, 10**6))
        yield msg


# -----------------------------------------------------
# Queue tests
# -----------------------------------------------------
def test_queue_insertion():
    """Test Queue insertion capabilities
    """
    queue = Queue()
    for msg in random_messages():
        queue.push(msg)

    selector = queue.__field_selector__

    last = None
    while queue:
        if last:
            _, new = queue.popitem()
            assert selector(new) > selector(last)
        else:
            _, new = queue.popitem()

        last = new





