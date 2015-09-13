# Event handlers
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

import nanolp.core as core

# Inspection (reflection) does not work on native funcs., so wrap they
def lower(s): return s.lower()
def lstrip(s): return s.lstrip()
def rstrip(s): return s.rstrip()
def strip(s): return s.strip()
def swapcase(s): return s.swapcase()
def title(s): return s.title()
def upper(s): return s.upper()
def joinargs(posargs, c='', j=''):
    """join positional arguments with 'j' symbol. Each
    argument may be transformed to upper case (c='u'),
    lower (c='l') or unchanged (c='')
    """
    if not c:
        c = lambda x: x
    elif c == 'u':
        c = lambda x: x.upper()
    elif c == 'l':
        c = lambda x: x.lower()
    return j.join(c(str(x)) for x in posargs)

core.EventHandler.register_func('lower', lower)
core.EventHandler.register_func('lstrip', lstrip)
core.EventHandler.register_func('rstrip', rstrip)
core.EventHandler.register_func('strip', strip)
core.EventHandler.register_func('swapcase', swapcase)
core.EventHandler.register_func('title', title)
core.EventHandler.register_func('upper', upper)
core.EventHandler.register_func('joinargs', joinargs)
