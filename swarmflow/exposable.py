# import inspect

def expose(*args, **kw):
    "Note that using **kw you can tag the function with any parameters"
    def wrap(func):
        name = func.func_name
        assert not name.startswith('_'), "Only public methods can be exposed"

        meta = func.__meta__ = kw
        meta['exposed'] = True
        meta['varnams'] =  func.func_code.co_varnames

        return func

    if args:
        return wrap(args[0])
    return wrap

class Exposable(object):
    "Base class to expose instance methods"
    _exposed_ = {}  # Not necessary, just for pylint

    class __metaclass__(type):
        def __new__(cls, name, bases, state):
            methods = state['_exposed_'] = dict()

            # inherit bases exposed methods
            for base in bases:
                methods.update(getattr(base, '_exposed_', {}))

            for name, member in state.items():
                meta = getattr(member, '__meta__', None)
                if meta is not None:
                    methods[name] = member
            return type.__new__(cls, name, bases, state)
