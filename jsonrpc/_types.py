import six
from functools import reduce


def _types_gen(T):
    yield T
    if hasattr(T, 't'):
        for l in T.t:
            yield l
            if hasattr(l, 't'):
                for ll in _types_gen(l):
                    yield ll


def _basetypes(T):
    return [t for t in _types_gen(T) if not isinstance(t, Type)]


class Type(type):
    """ A rudimentary extension to `type` that provides polymorphic
  types for run-time type checking of JSON data types. IE:

  assert type(u'') == String
  assert type('') == String
  assert type('') == Any
  assert Any.kind('') == String
  assert Any.decode('str') == String
  assert Any.kind({}) == Object
  """

    def __init__(self, *args, **kwargs):
        type.__init__(self, *args, **kwargs)

    def __eq__(self, other):
        if six.PY2:
            for T in _types_gen(self):
                if isinstance(other, Type):
                    if T in other.t:
                        return True
                if type.__eq__(T, other):
                    return True
        elif six.PY3:
            for T in _types_gen(self):
                if isinstance(other, Type) and T in other.t:
                    return True
                elif other in _basetypes(T):
                    return True
        return False

    def __str__(self):
        return "%s(%s)" % (getattr(self, '_name', 'unknown'), getattr(
            self, 't', None))

    def N(self, n):
        self._name = n
        return self

    def I(self, *args):
        self.t = list(args)
        return self

    def kind(self, t):
        if type(t) is Type:
            return t
        ty = lambda t: type(t)
        if type(t) is type:
            ty = lambda t: t
        return reduce(
            lambda L, R: R if (hasattr(R, 't') and ty(t) == R) else L,
            [T for T in _types_gen(self) if T is not Any])

    def decode(self, n):
        return reduce(lambda L, R: R if (str(R) == n) else L, _types_gen(self))


str_types = (six.text_type, )
if six.PY2:
    str_types += (six.binary_type, )
num_types = six.integer_types + (float, )

# JSON primitives and data types
Object = Type('Object', (object, ), {}).I(dict).N('obj')
Number = Type('Number', (object, ), {}).I(*num_types).N('num')
Boolean = Type('Boolean', (object, ), {}).I(bool).N('bit')
String = Type('String', (object, ), {}).I(*str_types).N('str')
Array = Type('Array', (object, ), {}).I(list, set, tuple).N('arr')
Nil = Type('Nil', (object, ), {}).I(type(None)).N('nil')
Any = Type('Any', (object, ), {}).I(
    Object, Number, Boolean, String, Array, Nil).N('any')
