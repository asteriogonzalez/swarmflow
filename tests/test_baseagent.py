import time
import random
from swarmflow.baseagent import SQueue, Message, FIRE, MSG_ID, BODY, genuid
from swarmflow.baseagent import default_key_selector, default__field_selector

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
    """Test Queue insertion capabilities.
    """
    queue = SQueue(
            __field_selector__=default__field_selector,
            __key_selector__=default_key_selector
        )
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





