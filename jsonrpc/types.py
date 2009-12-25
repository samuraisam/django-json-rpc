def _types_gen(T):
  yield T
  if hasattr(T, 't'):
    for l in T.t:
      yield l
      if hasattr(l, 't'):
        for ll in _types_gen(l):
          yield ll


class Type(type):
  """A rudimentary extension to `type` that provides polymorphic
  types for run-time type checking of JSON data types. IE:
  
  assert type(strobj) == String
  assert type(strobj) == Any
  """
  
  def __init__(self, *args, **kwargs):
    type.__init__(self, *args, **kwargs)
  
  def __eq__(self, other):
    for T in _types_gen(self):
      if isinstance(other, Type):
        if T in other.t:
          return True
      if type.__eq__(T, other):
        return True
    return False
  
  def __str__(self):
    return getattr(self, '_name', 'unknown')
  
  def N(self, n):
    self._name = n
    return self
  
  def I(self, *args):
    self.t = list(args)
    return self
  
  def kind(self, t):
    if type(t) is Type:
      return t
    return reduce(
      lambda L, R: R if (hasattr(R, 't') and type(t) == R) else L,
      filter(lambda T: T is not Any, 
        _types_gen(self)))
  
  def decode(self, n):
    return reduce(
      lambda L, R: R if (str(R) == n) else L,
      _types_gen(self))

# JSON primatives and data types
Object = Type('Object', (object,), {}).I(dict).N('obj')
Number = Type('Number', (object,), {}).I(int, long).N('num')
Boolean = Type('Boolean', (object,), {}).I(bool).N('bit')
String = Type('String', (object,), {}).I(str, unicode).N('str')
Array = Type('Array', (object,), {}).I(list, set).N('arr')
Nil = Type('Nil', (object,), {}).I(type(None)).N('nil')
Any = Type('Any', (object,), {}).I(
        Object, Number, Boolean, String, Array, Nil).N('any')