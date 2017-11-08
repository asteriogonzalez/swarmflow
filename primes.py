
from time import sleep
from itertools import chain
from random import shuffle, randint

from jug import TaskGenerator, bvalue


@TaskGenerator
def is_prime(n):
    print "is %s prime?" % n
    sleep(0.1)
    for j in range(2, n - 1):
        if (n % j) == 0:
            return False
    return True


M = randint(101, 200)

M = 5

print "Exploring %s first prime numbers" % M

inputs = range(2, M)

# shuffle(inputs)

primes = [is_prime(n) for n in inputs]

results = [i for i, k in zip(inputs, bvalue(primes)) if k]

print results

class Foo(object):
    def __init__(self, param=1):
        self.param = param

    @TaskGenerator
    def bar(self, n):
        return self.param + n


foo = Foo()

result = foo.bar(foo, 7)

print result.value()
