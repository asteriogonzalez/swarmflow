"""Sorted queue
"""

def default__field_selector__(item):
    "assume a list style object"
    return item[default_key_selector(item)]

def default_key_selector(item):
    "assume a list style object"
    return 0


class SQueue(dict):
    """A dictionary that sort element by some criteria.
    Inspided by OrderedDict.
    """
    def __init__(self, *args, **kwds):
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))

        self.__ordmap = list()
        self.__field_selector__ = kwds.pop('__field_selector__', default__field_selector__)
        self.__key_selector__ = kwds.pop('__key_selector__', default_key_selector)

    def __setitem__(self, key, value):
        # regular direct access
        dict.__setitem__(self, key, value)

        # order the key list
        v0 = self.__field_selector__(value)
        for idx, k1 in enumerate(self.__ordmap):
            if v0 < self.__field_selector__(self[k1]):
                self.__ordmap.insert(idx, key)
                break
        else:
            self.__ordmap.append(key)

    def push(self, value):
        key = self.__key_selector__(value)
        return self.__setitem__(key, value)

    def popitem(self, last=True):
        """queue.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned based on order criteria LIFO order if last is true or FIFO order if false.
        """
        while self.__ordmap:
            key =  self.__ordmap[0] if last else self.__ordmap[-1]
            try:
                value = self.pop(key)
                return key, value
            except KeyError:
                continue
        raise KeyError('dictionary is empty')

    def popitem2(self, last=True):
        """queue.popitem2() -> (s, v), return and remove a (key, value) pair.
        Return selector field and value
        """
        while self.__ordmap:
            key =  self.__ordmap[0] if last else self.__ordmap[-1]
            try:
                value = self.pop(key)
                return self.__field_selector__(value), value
            except KeyError:
                continue
        raise KeyError('dictionary is empty')

    def getitem(self, last=True):
        """queue.getitem() -> (k, s, v), return and remove a (key, value) pair.
        Return (key, selector field, value)
        """
        while self.__ordmap:
            key =  self.__ordmap[0] if last else self.__ordmap[-1]
            try:
                value = self.get(key)
                return key, self.__field_selector__(value), value
            except KeyError:
                continue
        raise KeyError('dictionary is empty')

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        self[key] = default
        return default

    def pop(self, key, default=None):
        """queue.pop(k[,d]) -> v, remove specified key and return the corresponding
        value.  If key is not found, d is returned if given, otherwise KeyError
        is raised.
        """
        self.__ordmap.remove(key)
        return dict.pop(self, key, default)
