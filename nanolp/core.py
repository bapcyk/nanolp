# Core of LP
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

__VERSION__ = '1.0'
__ABOUT__ = 'Nano LP, v. %s'%__VERSION__

import re
import os
import sys
import copy
import stat
import pprint
#import atexit
import string
import random
import inspect
import fnmatch
import datetime
import warnings
import calendar
import tempfile
import itertools
import functools
import xml.sax as sax
import xml.sax.saxutils as saxutils
from collections import OrderedDict, Callable, Iterable, namedtuple
from nanolp import _instlog

## dir. in sys.prefix with additional files
EXTRADIR = "nanolp-extra"

ANONDICTNAME = '_anon'
UNDEFINED = ['undefined']
## symbols can be escaped with \ in Cmd
CMDQUOTE = string.punctuation
## platform-independent constant
_O_BINARY = getattr(os, 'O_BINARY', 0)

## MS Windows running
_WIN = True if 'win' in sys.platform else False

################################################################################
# Python 2 -> 3 compatibility

_PY23 = 3 if sys.version_info.major > 2 else 2

# to avoid syntax errors (reraise23() for ex.) implements in different modules
if _PY23 == 2:
    from nanolp.lpcompat2 import *
elif _PY23 == 3:
    from nanolp.lpcompat3 import *

#################################################################################

# Utilities {{{
################################################################################

def pipecall(funcs, *args, **kwargs):
    """Special kind of calling funcs with pipeling arguments:
    args, kwargs -> f1 -> .. -> result_args, result_kwargs
    """
    _args = args[:]; _kwargs = kwargs.copy()
    for f in funcs:
        _args, _kwargs = f(*_args, **_kwargs)
    return (_args, _kwargs)

# NOTE no any relation to Chunk._subargs/subargs !
def subargs(key, *args, **kwargs):
    """Substitute all '$...' in args and kwargs, returns modified (args, kwargs)
    with resolver key - dict or func: '...'->value

    >>> d = {'a': '$x'}
    >>> subargs({'x':123}, 1, 2, '$x', **d)
    ((1, 2, 123), {'a': 123})
    >>> d['a'] # d not changed!
    '$x'
    """
    if key is None: return (args, kwargs)
    elif type(key) is dict: key = lambda f, _d=key: _d.get(f, None)
    elif not isinstance(key, Callable):
        raise ValueError("'key' argument should be function or map")

    def resolve(x):
        if isinstance(x, StringTypes23) and x.startswith('$'):
            return key(x[1:])
        else: return x

    args = tuple(resolve(a) for a in args)
    kwargs = {k:resolve(v) for k,v in kwargs.items()}
    return (args, kwargs)

def splittokens(text):
    """Split string to tokens

    >>> splittokens('')
    []
    >>> splittokens('aa bb')
    ['aa', 'bb']
    >>> splittokens('aa "bb cc"')
    ['aa', 'bb cc']
    >>> splittokens('aa ""')
    ['aa', '']
    >>> splittokens("aa 'bb cc'")
    ['aa', 'bb cc']
    >>> splittokens("aa 'bb \\" cc'")
    ['aa', 'bb " cc']
    """
    EOL = '\0' # end-of-line
    TXT, SQ, DQ, END = 0, 1, 2, 3 # states (in text, in single quote, in double quote)
    st = TXT
    tmp = ''
    result = []
    text += EOL
    for ch in text:
        if st == END:
            break
        elif st == TXT:
            if ch == EOL:
                if tmp: result.append(tmp); tmp = ''
                st = END
            elif ch in (' ', '\t'):
                if tmp: result.append(tmp); tmp = ''
            elif ch == "'":
                st = SQ
            elif ch == '"':
                st = DQ
            else: tmp += ch
        elif st == SQ:
            if ch == EOL: raise ValueError("unbalanced '")
            elif ch == "'":
                result.append(tmp); tmp = ''
                st = TXT
            else: tmp += ch
        elif st == DQ:
            if ch == EOL: raise ValueError('unbalanced "')
            elif ch == '"':
                result.append(tmp); tmp = ''
                st = TXT
            else: tmp += ch
    return result

def parseopt(text, kwargs={}):
    """Like getopt. text is input string, kwargs - dict. of default arguments values,
    if one is boolean then it'll be treat as flag (need not value: '-f', not '-f VAL').
    Returns pair of positional args. list and keyword args. dictionary

    >>> kw = {'-par': False}
    >>> p,k = parseopt("open -par -baud '9600, 8b' $a.b", kw)
    >>> p
    ['open', '$a.b']
    >>> sorted(k.keys())
    ['-baud', '-par']
    >>> k['-baud'], k['-par']
    ('9600, 8b', True)
    """
    NOMORE, EOO = 0, 1 # special symbols (end-of-line, end-of-options)
    OPT, VAL, END = 0, 1, 2 # states

    _posargs = []
    _kwargs = kwargs.copy()

    isKw = lambda s: s and s[0]=='-'
    setPosArg = lambda opt: _posargs.append(opt)
    def setKwArg(name, val):
        ret = NOMORE
        if name:
            defaultValue = kwargs.get(name)
            if isinstance(defaultValue, bool):
                if not val: val = True
                elif isinstance(val, bool):
                    ret = val
                    val = True
            _kwargs[name] = val
        return ret

    kw = ''
    state = OPT # OPT|VAL|END
    arguments = splittokens(text)
    arguments.append(EOO)
    for opt in arguments:
        if state == OPT:
            if opt == EOO: state = END
            elif isKw(opt):
                kw = opt
                state = VAL
            else: setPosArg(opt)
        elif state == VAL:
            if opt == EOO:
                setKwArg(kw, '')
                state = END
            elif isKw(opt):
                setKwArg(kw, '')
                kw = opt
            else:
                maybePos = setKwArg(kw, opt)
                if maybePos != NOMORE: setPosArg(maybePos)
                state = OPT
        elif state == END:
            break
    return (_posargs, _kwargs)

#class LazyCurryFunc:
#    """
#    Can be used to make curried and deferred call. Also wrapping is
#    support, for LP syntax in 'on' commands, ex. 'do.EVENT: lower $argX'
#    using wrap it's possible to call 'lower' func on 'argX' argument
#    from kwargs:
#        posargs, kwargs = lazycurryfunc(...).wrap(wf)()
#    wf should be func:
#        wf(lazycurryfunc, *orig_posargs, **orig_kwargs) -> new_posargs, new_kwargs
#    It may be used in pipe style calling
#
#    >>> transparent = lambda *a, **kw: (a, kw)
#    >>> def w(lcf, *args, **kwargs):
#    ...     if len(lcf.argspec[0])==1 and lcf.argspec[0][0].startswith('$'):
#    ...         argname = lcf.argspec[0][0][1:]
#    ...         singlearg = kwargs[argname]
#    ...         singlearg = lcf.func(singlearg)
#    ...         kwargs[argname] = singlearg
#    ...         return (args, kwargs)
#    ...     else:
#    ...         return None # default calling
#    >>> upper = lambda s: s.upper()
#    >>> lcf = parselnexp('g $x', {'g':upper})
#    >>> lcf.wrap(w)(1, 2, 3, x='xxx')
#    ((1, 2, 3), {'x': 'XXX'})
#
#    >>> lcf = parselnexp('g 0', {'g':transparent})
#    >>> lcf.wrap(w)(1, 2, 3, x='xxx')
#    (('0', 1, 2, 3), {'x': 'xxx'})
#
#    >>> lcf = parselnexp('g a b', {'g':transparent})
#    >>> lcf.wrap(w)(1, 2, 3, x='xxx')
#    (('a', 'b', 1, 2, 3), {'x': 'xxx'})
#    """
#    ## custom action func: *a,**kw -> ...
#    func = None
#    ## wrapper for func:
#    ##  wrapfunc(LazyCurryFunc, *orig_posargs, **orig_kwargs) -> new_posargs, new_kwargs
#    wrapfunc = None
#    ## pair (posargs,kwargs) - result of parsing
#    argspec = None
#    ## real args for curry (partial), default are = argspec (can be rebound)
#    args = None
#
#    def __init__(self, func, *args, **kwargs):
#        self.func = func
#        self.wrapfunc = None
#        self.argspec = (args, kwargs)
#        self.args = [args, kwargs]
#    def bindargs(self, args, kwargs):
#        self.args = [args, kwargs]
#    def __call__(self, *args, **kwargs):
#        if self.wrapfunc:
#            wrapret = self.wrapfunc(self, *args, **kwargs)
#            if wrapret is not None:
#                return wrapret # modified args (args, kwargs)
#        # if no wrapfunc or wrapfunc returned None
#        callposargs, callkwargs = self.args
#        curry = functools.partial(self.func, *callposargs, **callkwargs)
#        return curry(*args, **kwargs)
#    def wrap(self, func):
#        """Set wrapper-function of curried func"""
#        self.wrapfunc = func
#        return self

FuncInfo = namedtuple('FuncInfo', ['funcname', 'posargs', 'kwargs'])

def parselnexp(text):
    """Parse text (one line expr.) like 'cmd -arg1 a -arg2 b c d' into
    FuncInfo

    """
    #if type(key) is dict: key = lambda f, _d=key: _d.get(f, None)
    #elif not isinstance(key, Callable): raise ValueError("'key' argument should be function or map")

    posargs, kwargs = parseopt(text)
    if not posargs: raise ValueError('Command name is missed in script line')
    cmd = posargs[0]; posargs = posargs[1:]

    #func = key(cmd) or locals().get(cmd, None) or globals().get(cmd, None) \
            #or getattr(builtins, cmd, None)
    #if not func: raise ValueError("No such command '%s'"%cmd)
    return FuncInfo(funcname=cmd, posargs=posargs, kwargs=kwargs)
    #curryfunc = functools.partial(func, *posargs, **kwargs)
    #curryfunc.argspec = (posargs, kwargs)
    #lazycurryfunc = LazyCurryFunc(func, *posargs, **kwargs)
    #return lazycurryfunc

# used in test.config still
def TCP_PORT(minmax):
    """Return safe TCP port. minmax is integer or list|tuple - range.
    If one of them is lesser then 1024, it will be set to 1024.
    If 2nd is omitted, 65535 will be used. When is range, random will
    be generated

    >>> TCP_PORT(1)
    1024
    >>> TCP_PORT(9000), TCP_PORT(9000)
    (9000, 9000)
    >>> TCP_PORT([1]) > 1024
    True
    >>> TCP_PORT([45000]) > 45000
    True
    >>> 45000 <= TCP_PORT([45000, 45002]) <= 45002
    True
    """
    if isinstance(minmax, (list, tuple)):
        # it's range
        min = minmax[0]; max = minmax[1] if len(minmax)>1 else 65535
        if min < 1024 or min > 65535: min = 1024
        if max < 1024 or max > 65535: max = 65535
        if min > max: min, max = max, min
        return random.randint(min, max)
    else:
        return minmax if minmax >= 1024 else 1024

def default_attributes(**attrs):
    """Create class with default attributes values and
    disable adding new attributes"""
    class _FakeClass(object):
        __defaults__ = attrs
        def __setattr__(self, a, v):
            if a not in self.__defaults__.keys():
                raise AttributeError(a)
            else:
                super(_FakeClass, self).__setattr__(a, v)
        def __init__(self):
            for a, v in self.__defaults__.items():
                super(_FakeClass, self).__setattr__(a, v)
    return _FakeClass

def isint(x):
    """Test that x is int presentation

    >>> isint(9)
    True
    >>> isint('-10')
    True
    >>> isint('a')
    False
    """
    try:
        int(x)
    except: return False
    else: return True

def url2path(url, fragments=False):
    """Convert <scheme>://... to path. If fragments, returns [path, fragments...]

    >>> url2path('file:///a/b/c')
    '/a/b/c'
    >>> url2path('file://localhost/a/b/c')
    '/a/b/c'
    >>> url2path('file://localhost:8000/a/b/c')
    '/a/b/c'
    >>> url2path('zip:/a/b/c#x/y.md')
    '/a/b/c'
    >>> url2path('zip:a/b/c#x/y.md', True)
    ['a/b/c', 'x/y.md']
    >>> url2path('http://localhost:8000/a/b/c#x/y.md')
    '/a/b/c'
    >>> url2path('http://localhost:8000/a/b/c#x1#x2#x3', True)
    ['/a/b/c', 'x1', 'x2', 'x3']
    """
    a = urlsplit(url)
    # convert path
    path = urlunquote(a.path)
    #path = path.strip('/')
    #if not os.path.splitdrive(path)[0]:
        # first is not DRIVE (in Windows), so make it root
        #path = '/' + path.replace('\\', '/')
    #path = os.path.normpath(path)
    pa = path.split('#')
    path = pa[0]
    if _WIN:
        # XXX MSWin fixing: if path looks '/c:/..' or '\c:\...', del 1st /
        path = re.sub(r'^[/\\](\w:[/\\])', r'\1', path)
    if fragments:
        ret = [path]
        ret.extend(f for f in itertools.chain(pa[1:], a.fragment.split('#')) if f)
        return ret
    else: return path

def path2url(path, scheme, netloc='', fragment=''):
    """Convert FS-path to URL with scheme

    >>> p = 'a/b/c'
    >>> p1 = path2url(p, 'file')
    >>> os.path.normpath(url2path(p1)) == os.path.abspath(p)
    True
    >>> p1 = path2url(p, 'zip')
    >>> os.path.normpath(url2path(p1)) == os.path.abspath(p)
    True
    """
    path = os.path.abspath(path)
    path = urlquote(path.replace('\\', '/'))
    return urlunsplit((scheme, netloc, path, '', fragment))

def extrapath(p):
    """Return path in directory of extras files if p is relative
    path, otherwise - p itself"""
    if os.path.isabs(p): return p
    else: return os.path.join(extradir(), p)

def extradir():
    """Return full path to directory of extras files"""
    return os.path.join(_instlog.DATA_DIR, EXTRADIR)

def fix_crlf(buf):
    """Translate \r\n -> \n (actual for binary file)
    """
    return buf.replace('\r\n', '\n')

def normnegindex(i, count):
    """Normalize negative index i of count items

    >>> normnegindex(0, 4)
    0
    >>> normnegindex(1, 4)
    1
    >>> normnegindex(-1, 4)
    3
    >>> normnegindex(-4, 4)
    0
    >>> normnegindex(-5, 4) is None
    True
    """
    if i >= 0: return i
    i = abs(i)
    if i > count: return None
    return count - i

def absurl(urlstr, path):
    """Like abspath but for URL

    >>> absurl('http://web.site.com/a/b?x=1&y=2', 'xxx.md')
    'http://web.site.com/a/xxx.md?x=1&y=2'
    >>> absurl('http://web.site.com/a/b?x=1&y=2', '/xxx.md')
    'http://web.site.com/xxx.md?x=1&y=2'
    >>> absurl('http://web.site.com/a/b/c?x=1&y=2', '../xxx.md')
    'http://web.site.com/a/xxx.md?x=1&y=2'
    >>> absurl('http://web.site.com/a/b/', 'xxx.md')
    'http://web.site.com/a/b/xxx.md'
    >>> absurl('http://web.site.com/a/b', 'xxx.md')
    'http://web.site.com/a/xxx.md'
    >>> absurl('http://web.site.com/a', '/xxx.md')
    'http://web.site.com/xxx.md'
    >>> absurl('http://localhost:8000/example.md', 'xxx.md')
    'http://localhost:8000/xxx.md'
    """
    spl = urlsplit(urlstr)
    if path.startswith('/'):
        spl = spl._replace(path=path)
    else:
        curpath = os.path.dirname(spl.path)
        if curpath and curpath != '/':
            path = os.path.normpath('/'.join((curpath, path)))
            path = path.replace(os.sep, '/')
        spl = spl._replace(path=path)
    return urlunsplit(spl)

def updatedict(dst, src, *onlykeys, **additional):
    """Update dst dictionary from src with only keys,
    and add additional values

    >>> r = updatedict({}, {'a':1, 'b':2, 'c':3}, 'c', 'a', x=10)
    >>> sorted(r.keys())
    ['a', 'c', 'x']
    >>> r['a'], r['c'], r['x']
    (1, 3, 10)
    """
    if not onlykeys: dst.update(src)
    else: dst.update((k,v) for k,v in src.items() if k in onlykeys)
    dst.update(additional)
    return dst

def islices(seq, num):
    """Cuts sequence seq on slices with length num.
    Each slice is iterator on its elements. Yielding
    will be to the end of sequence. To finish early,
    use close() of Generator

    >>> res = []
    >>> for sl in islices((1,2,3,4,5,6,7,8,9,0), 4):
    ...     for x in sl: res.append(x)
    ...     res.append('--')
    >>> res
    [1, 2, 3, 4, '--', 5, 6, 7, 8, '--', 9, 0, '--']
    """
    if num <= 0:
        raise ValueError("num must be > 0")

    # find 'empty' - criteria of iteration end
    try:
        # if 'seq' has len, limit yielding of slices with it
        length = len(seq)
        empty = lambda abeg: abeg >= length
    except:
        empty = lambda _:False

    # else for list/tuple will yield 0,1,2; 0,1,2; 0,1,2.. instead of 0,1,2; 3,4,5..
    seq = iter(seq)
    beg = 0
    while not empty(beg):
        yield itertools.islice(seq, 0, num)
        beg += num 

def indentstr(text, from_):
    """Looks for indent in text from 'from_' position in reverse order.
    But if from_ is 0 - in direct order

    >>> indentstr('012345 aaa', 7)
    ''
    >>> indentstr('   aaa', 3)
    '   '
    >>> indentstr('\\n    aaa', 5)
    '    '
    >>> indentstr('aaa', 0)
    ''
    >>> indentstr('  aaa', 0)
    '  '
    """
    if from_ == 0:
        # direct order indent lookup
        i = 0
        while i < len(text):
            if text[i] not in (' ', '\t'):
                break
            i += 1
        # cut indent part
        return text[:i]

    else:
        # reverse order indent lookup
        i = from_-1
        while i >= 0:
            if text[i] not in (' ', '\t'):
                break
            i -= 1
        # cut indent part
        if i == -1:
            return text[:from_]
        elif text[i] in ('\n', '\r'):
            return text[i+1:from_]
        else:
            return ''

def indenttext(text, indent, first=False, cr='\n'):
    """Indent text block with indent string (split to lines, then
    join to lines with 'cr' symbol. If first is True, then indent
    also first line too

    >>> indenttext('aaa\\nbbb', '  ')
    'aaa\\n  bbb'
    >>> indenttext('aaa\\nbbb', '  ', first=1)
    '  aaa\\n  bbb'
    """
    lines = text.splitlines()
    for i in range(0 if first else 1, len(lines)):
        lines[i] = indent + lines[i]
    return cr.join(lines)

def deltextindent(text, cr='\n'):
    """Remove indentation of text

    >>> deltextindent('  a\\n   b\\n    c')
    'a\\n b\\n  c'
    >>> deltextindent('a\\n  b\\n   c')
    'a\\n  b\\n   c'
    >>> deltextindent(' a\\n\\n\\n  b\\n   c')
    'a\\n\\n\\n b\\n  c'
    >>> deltextindent('\\n  a\\n\\n  b')
    '\\na\\n\\nb'
    >>> text = '\\n  aaa\\n    bbb\\n\\n\\n  cc\\n'
    >>> deltextindent(text)
    '\\naaa\\n  bbb\\n\\n\\ncc'
    """
    lines = text.splitlines()
    minindent = min(len(indentstr(s, 0)) for s in lines if s)
    return cr.join(s[minindent:] for s in lines)

def user_input(msg, chkfunc=None, prompt='\n> ', quiet=False):
    """Read from user input (on colsole), returns entered text. msg is the
    message to user. If chkfunc is used, should be chkfunc(entered) and returns
    error message if input is incorrect or nothing otherwise"""
    if quiet:
        raise RuntimeError('Can not input from console in quiet mode')
    inp = None
    while True:
        inp = raw_input23(msg + prompt)
        if chkfunc:
            errmsg = chkfunc(inp)
            if errmsg:
                prn(errmsg, file='stderr', quiet=quiet)
                continue
            else:
                break
        else: break
    return inp

def prn(*args, **opts):
    """Write args serially (without spacing, or with delimiter
    opts['delim']), with newline (or without if opts['nonl']),
    to stdout (or any other opts['file']).
    Nothing does if opts['engine'].quiet or opts['quiet']
    """
    quiet = opts.get('quiet', False)
    if not quiet:
        engine = opts.get('engine', None)
        if engine:
            quiet = engine.quiet
    # now test if needed output
    if quiet: return

    delim = opts.get('delim', '')
    s = delim.join(args)
    if not opts.get('nonl', False): s+= '\n'
    out = opts.get('file', '')
    if out == 'null' or out == '/dev/null':
        return
    elif out == 'stdout':
        sys.stdout.write(s)
    elif out == 'stderr':
        sys.stderr.write(s)
    else:
        fwrite23(out, s, mode='a+t')

################################################################################
# }}}

# Pure HTML parser/serializator {{{
################################################################################

class HTMLToken(object):
    """For serializing some HTML object

    >>> str(HTMLToken(tag='html'))
    '<html>'
    >>> str(HTMLToken(tag='table', attrs='a=1|b=2', data='ddd'))
    '<table a="1" b="2">ddd'
    >>> str(HTMLToken(tag='br', kind=HTMLToken.SINGLE))
    '<br/>'
    >>> str(HTMLToken(data='<!-- comment -->'))
    '<!-- comment -->'
    >>> str(HTMLToken(attrs='a=1|b=2', data='<!-- comment -->', kind=HTMLToken.CLOSE))
    '<!-- comment -->'
    >>> str(HTMLToken(data='ddd', attrs='a=1|b=2', tag='div', kind=HTMLToken.SINGLE))
    '<div a="1" b="2"/>'
    >>> str(HTMLToken(data='ddd', attrs='a=1|b=2', tag='div', kind=HTMLToken.OPEN))
    '<div a="1" b="2">ddd'
    """

    OPEN, CLOSE, SINGLE = 0, 1, 2

    def __init__(self, tag='', attrs={}, data='', kind=OPEN):
        _attrpair = lambda s: (s.strip() for s in s.split('='))
        self.tag = tag
        if isinstance(attrs, (list, tuple)):
            self.attrs = OrderedDict(attrs)
        elif isinstance(attrs, StringTypes23):
            self.attrs = OrderedDict(_attrpair(p) for p in attrs.split('|'))
        else:
            self.attrs = attrs
        self.data = data
        self.kind = kind

    def __repr__(self):
        # attrs
        if self.attrs:
            if isinstance(self.attrs, StringTypes23):
                attrs = ' ' + self.attrs
            else:
                attrs = ' ' + ' '.join('%s="%s"'%(k,v) for k,v in self.attrs.items())
        else:
            attrs = ''
        # tag
        if self.tag:
            if self.kind == HTMLToken.SINGLE:
                res = ['<%s%s/>'%(self.tag, attrs)]
                expdata = False # is data expected?
            elif self.kind == HTMLToken.OPEN:
                res = ['<%s%s>'%(self.tag, attrs)]
                expdata = True
            elif self.kind == HTMLToken.CLOSE:
                res = ['</%s>'%self.tag]
                expdata = False # is data expected?
        else:
            res = []; expdata = True
        # data
        if expdata and self.data:
            res.append(self.data)
        return ''.join(res)

    def __rich_strcmp(self, s, patt, ic=False):
        """Compares patt and s. If patt is '/xxx/', use regular expression.
        ic is ignore case flag"""
        if patt.startswith('/') and patt.endswith('/'):
            if not re.search(patt[1:-1], s): return False
        else:
            if ic:
                if patt.lower() != s.lower(): return False
            else:
                if patt != s: return False
        return True

    def __rich_dictcmp(self, d, patt):
        """Compares dict. patt and dict. d. Items in patt may be 'k':'/xxx/' or
        string value of object
        """
        for pattk, pattv in patt.items():
            v = d.get(pattk, None)
            if v is None: return False
            elif not self.__rich_strcmp(str(v), pattv): return False
        return True

    def match(self, token=UNDEFINED, tag=UNDEFINED, attrs=UNDEFINED, data=UNDEFINED, kind=UNDEFINED):
        if token is not UNDEFINED:
            return self.match(tag=token.tag, attrs=token.attrs, data=token.data, kind=token.kind)
        else:
            if tag is not UNDEFINED and not self.__rich_strcmp(self.tag, tag, ic=True):
                return False
            if attrs is not UNDEFINED and not self.__rich_dictcmp(self.attrs, attrs):
                return False
            if data is not UNDEFINED and not self.__rich_strcmp(self.data, data):
                return False
            if kind is not UNDEFINED and kind != self.kind:
                return False
        return True

################################################################################

class HTMLSpecToken(HTMLToken):
    """Handles special tokens like entity refs. etc.

    >>> str(HTMLERefToken('gt'))
    '&gt;'
    >>> str(HTMLCommToken('gt'))
    '<!--gt-->'
    """

    def __init__(self, data):
        self.specdata = data
        HTMLToken.__init__(self, data=self.fmt%data)

################################################################################

class HTMLERefToken(HTMLSpecToken):
    """Entity reference"""
    fmt = '&%s;'
class HTMLCRefToken(HTMLSpecToken):
    """Char reference"""
    fmt = '&#%s;'
class HTMLCommToken(HTMLSpecToken):
    """Comment"""
    fmt = '<!--%s-->'
class HTMLDeclToken(HTMLSpecToken):
    """Declaration"""
    fmt = '<!%s>'
class HTMLPiToken(HTMLSpecToken):
    """Process instruction"""
    fmt = '<?%s>'
class HTMLUnkToken(HTMLSpecToken):
    """Unknown declaration"""
    fmt = '<![%s]>'

#################################################################################

class HTMLTokensStream(HTMLParser):
    """Parse HTML to tokens stream"""
    def __init__(self, strict=False):
        self.tokens = []
        if _PY23 == 3:
            HTMLParser.__init__(self, strict)
        else:
            HTMLParser.__init__(self)

    def handle_any(self, token):
        """Is called after create token and before saving. Result is
        saving in stream, None - token is omitted
        """
        return token

    def handle_startendtag(self, tag, attrs):
        token = HTMLToken(tag=tag, attrs=attrs, kind=HTMLToken.SINGLE)
        token = self.handle_any(token)
        if token: self.tokens.append(token)

    def handle_starttag(self, tag, attrs):
        token = HTMLToken(tag=tag, attrs=attrs, kind=HTMLToken.OPEN)
        token = self.handle_any(token)
        if token: self.tokens.append(token)

    def handle_endtag(self, tag):
        token = HTMLToken(tag=tag, kind=HTMLToken.CLOSE)
        token = self.handle_any(token)
        if token: self.tokens.append(token)

    def handle_charref(self, name):
        token = HTMLCRefToken(data=name)
        token = self.handle_any(token)
        if token: self.tokens.append(token)

    def handle_entityref(self, name):
        token = HTMLERefToken(data=name)
        token = self.handle_any(token)
        if token: self.tokens.append(token)

    def handle_data(self, data):
        token = HTMLToken(data=data)
        token = self.handle_any(token)
        if token: self.tokens.append(token)

    def handle_comment(self, data):
        token = HTMLCommToken(data=data)
        token = self.handle_any(token)
        if token: self.tokens.append(token)

    def handle_decl(self, decl):
        token = HTMLDeclToken(data=decl)
        token = self.handle_any(token)
        if token: self.tokens.append(token)

    def handle_pi(self, data):
        token = HTMLPiToken(data=data)
        token = self.handle_any(token)
        if token: self.tokens.append(token)

    def unknown_decl(self, data):
        token = HTMLUnkToken(data=data)
        token = self.handle_any(token)
        if token: self.tokens.append(token)

    ################################################

    def serialize(self):
        """Yields strings"""
        for token in self.tokens:
            yield str(token)

    def dom(self):
        """Return DOM"""
        # TODO

################################################################################
# }}}

################################################################################

class CmdSyntax:
    """Syntax parsing of command; syntax utilities of command
    """

    ## currsounder symbols (2 or 4)
    _surr = None
    ## surr. symbols stack (for pushing/poping instead of changing)
    _surrstack = None
    ## regexps templates (as dict.)
    _re = None

    def _reset(self):
        self._surr = {}
        self._surrstack = []
        self._re = {}

    def __init__(self, surr=None):
        self._reset()
        self.setsurr(surr)
        self._re = {
            # token: regexp ({0} - left surr, {1} - right surr)
            'cmddef': '{0}(?!=)(.+?){1}',
            'cmdsubst': '{0}=.+?{1}',
            'argsubst': '\$[^ $]+',
            'concrcmdsubst': '{0}={path}(,.+?)?{1}'
        }

    def getsurr(self):
        return self._surr['def'] + self._surr['subst']

    def pushsurr(self, surr):
        """Change surr. symbols but save last in stack

        >>> cs = CmdSyntax(('@', '@'))
        >>> cs.getsurr()
        ('@', '@', '@', '@')
        >>> cs.pushsurr(('(', ')', '<<', '>>'))
        >>> cs.getsurr()
        ('(', ')', '<<', '>>')
        >>> cs.popsurr()
        >>> cs.getsurr()
        ('@', '@', '@', '@')
        """
        self._surrstack.append(self.getsurr())
        self.setsurr(surr)

    def popsurr(self):
        """Restore last surr. symbols (saving with pushsurr())
        """
        surr = self._surrstack.pop()
        self.setsurr(surr)

    def setsurr(self, surr):
        """Change surr. symbols. surr is list of 2 symbols or 4. If 2 then
        they is using as surr. symbols when cmd. is defining and pasting.
        If 4 then first 2 are using as surr. symbols for cmd. definition, and
        last 2 - for pasting
        """
        if not surr: surr = ('<<', '>>')
        # set surr. symbols for cmd. definition and cmd. substitution (pasting)
        if len(surr) == 2:
            self._surr['def'] = tuple(surr)
            self._surr['subst'] = tuple(surr)
        elif len(surr) > 2:
            self._surr['def'] = tuple(surr[0:2])
            self._surr['subst'] = tuple(surr[2:4])

    def surround(self, context, text):
        """Surround some text with surr. symbols actual for context ('def'|'subst')

        >>> cs = CmdSyntax(['(', ')', '[[', ']]'])
        >>> cs.surround('def', 'xxx')
        '(xxx)'
        >>> cs.surround('subst', 'xxx')
        '[[xxx]]'
        """
        return '{0}{text}{1}'.format(*self._surr[context], text=text)

    def _getre(self, token, **kw):
        """Returns regexp

        >>> cs = CmdSyntax(['(', ')', '[[', ']]'])
        >>> cs._getre('cmddef')
        '\\\((?!=)(.+?)\\\)'
        >>> cs._getre('concrcmdsubst', path='xxx')
        '\\\[\\\[=xxx(,.+?)?\\\]\\\]'
        """
        e = self._re[token]
        if token in ('cmddef',): surr = self._surr['def']
        elif token in ('cmdsubst', 'concrcmdsubst'): surr = self._surr['subst']
        else: surr = []
        return e.format(*(re.escape(s) for s in surr), **kw)

    def findtokens(self, token, text, flags=None, **kw):
        """Find (iterator) of all parameterized by kw tokens in text with re flags
        """
        e = self._getre(token, **kw)
        reargs = [e, text]
        if flags: reargs.append(flags)
        it = re.finditer(*reargs)
        for m in it: yield m

    def subtokens(self, token, repl, text, count=0, flags=None, **kw):
        """Substitute token, parameterized by kw with repl (may be func) count times
        with re flags

        >>> cs = CmdSyntax(['(', ')', '[[', ']]'])
        >>> cs.subtokens('cmdsubst', 'xxx', 'Aaa [[=one]] and [[=two]] bbb', count=1)
        'Aaa xxx and [[=two]] bbb'
        >>> cs.subtokens('cmdsubst', 'xxx', 'Aaa [[=one]] and [[=two]] bbb')
        'Aaa xxx and xxx bbb'
        """
        e = self._getre(token, **kw)
        reargs = [e, repl, text, count]
        if flags: reargs.append(flags)
        return re.sub(*reargs)

    def istoken(self, token, text, flags=None, **kw):
        """Test if text is matched by parameterized with kw token with re flags

        >>> cs = CmdSyntax()
        >>> cs.istoken('cmddef', '<<a.b.c>>')
        True
        >>> cs.istoken('cmddef', 'a.b.c')
        False
        >>> cs.istoken('argsubst', 'c')
        False
        >>> cs.istoken('argsubst', '$c')
        True
        >>> cs.istoken('concrcmdsubst', '<<=x.y>>', path='x.y')
        True
        >>> cs.istoken('concrcmdsubst', '<<=x.y>>', path='x')
        False
        """
        e = self._getre(token, **kw)
        reargs = [e, text]
        if flags: reargs.append(flags)
        return bool(re.match(*reargs))

    def strip(self, text):
        """Try to treats text ad cmd. definition or cmd. substitution and to remove
        surr. symbols for both cases. But if text seems to be something another,
        returns the same text

        >>> cs = CmdSyntax(['(', ')', '[[', ']]'])
        >>> cs.strip('(abc)')
        'abc'
        >>> cs.strip('123')
        '123'
        >>> cs.strip('[[123]]')
        '[[123]]'
        >>> cs.strip('[[=a b c]]')
        '=a b c'
        """
        if self.istoken('cmddef', text):
            l, r = self._surr['def']
            return text[len(l):len(text)-len(r)]
        elif self.istoken('cmdsubst', text):
            l, r = self._surr['subst']
            return text[len(l):len(text)-len(r)]
        else:
            return text

################################################################################

class CmdError(Exception): pass

class Cmd:
    """Parse text into internal fields

    Events mechanism
    ================

    Are calling now:
    
    If recepient of event has method __onEVENT__() - it call, nothing else.
    Else parser.emitevent() create LineExp + Python object onEVENT() + instance-based
    handlers + class-based handlers (which canhandle() this event for this recepient)
    and call this chain.
    Class-based handlers are created by <<on.*>> cmd: <<on.CLASS.EVENT, do:...>> or
    <<on.CLASS, do.EVENT1:..., do.EVENT2:...>>. Instance-based handlers are created
    in any user-command (macros!) by <<some, do.EVENT1:..., do.EVENT2:...>>.
    Class-basd needs 'gpath' arg. necessary!
    
    So, scheme is:

        recep., event - matching -> onEVENT() + handlers
                                              |
                                             do!

    onEVENT() is callback of successor, it should call BaseClass.onEVENT()

    """
    ## description of command
    descr = ''
    ## global path matcher for class factory (Cmd-for not matched)
    gpath = None
    ## registered Cmd successors (or used base Cmd)
    commands = []
    ## CmdSyntax instance (static)
    syntax = CmdSyntax()
    ## is registered command or not
    _isregistered = False

    ## original text
    text = None
    ## pasting or definition
    ispaste = None
    ## set of commands or one ('*' is used in path)
    isset = None
    ## list of path components (with possible '*')
    path = None
    ## list of pairs: (key, value)
    args = None
    ## list of unnamed args
    body = None
    ## indent string
    indent = None
    ## source info dict (set by ondefine())
    srcinfo = None; SrcInfo = default_attributes(infile='')
    ## additional info related to multiple parts
    setinfo = None; SetInfo = default_attributes(size=1)

    def _reset(self):
        """Reset internal fields"""
        self.text = ""
        self.ispaste = False
        self.isset = False
        self.path = []
        self.args = []
        self.body = []
        self.indent = ''
        self.srcinfo = self.SrcInfo()
        self.setinfo = self.SetInfo()

    def __init__(self, text=None, indent='', cmd=None, setinfo=None):
        """Init from another cmd, or from text
        """
        if cmd:
            self._reset()
            SKIP = ('gpath', 'commands')
            self.__dict__.update((k,v) for k,v in cmd.__dict__.items() if k not in SKIP)
        else:
            self._reset()
            if text is not None:
                if not Cmd.syntax.istoken('cmddef', text) \
                        and not Cmd.syntax.istoken('cmdsubst', text):
                    # seems path, not cmd. definition
                    text = Cmd.syntax.surround('def', text)
                self.parse(text)
            self.indent = indent
            if setinfo:
                self.setinfo = setinfo

    @staticmethod
    def register(cmd):
        """Register new special command"""
        cmd._isregistered = True
        Cmd.commands.append(cmd)

    @staticmethod
    def get_uniform_commands(name):
        """Returns command and all it's successors. 'name' is string
        """
        for basecmd in Cmd.commands:
            if basecmd.__name__ == name:
                break
        else:
            # base Cmd class was not found
            return []
        ret = []
        for cmd in Cmd.commands:
            if issubclass(cmd, basecmd):
                ret.append(cmd)
        return ret

    @staticmethod
    def create_cmd(text=None, indent='', setinfo=None):
        """Cmd factory, returns INSTANCE

        >>> c = Cmd.create_cmd('<<use, file.h>>')
        >>> isinstance(c, UseCmd)
        True
        >>> c = Cmd.create_cmd('<<file.x, file.h>>')
        >>> isinstance(c, UseCmd)
        False
        """
        cmd = Cmd(text=text, indent=indent, setinfo=setinfo)
        for cls in Cmd.commands:
            if cmd.matchpath(cls.gpath):
                return cls(cmd=cmd)
        else:
            return cmd

    @staticmethod
    def isregistered(c):
        """Check that c (Cmd instance or text) is registered command. If
        returns False then c is user command (definition!)
        """
        if isinstance(c, StringTypes23):
            c = Cmd.create_cmd(c)
        return c._isregistered

    @staticmethod
    def pathindex(path):
        """Return last path component (index) in indexed path (if it is),
        None otherwise. Indexed path has more then 1 component and last
        component is positive or negative number

        >>> Cmd.pathindex('a.b') is None
        True
        >>> Cmd.pathindex('a.2')
        2
        >>> Cmd.pathindex('a.-3')
        -3
        >>> Cmd.pathindex('a') is None
        True
        >>> Cmd.pathindex('') is None
        True
        """
        if isinstance(path, StringTypes23):
            path = path.split('.')
        if len(path) < 2:
            return None
        else:
            try: return int(path[-1])
            except: return None

    @staticmethod
    def changepathindex(path, new_index):
        """If path has numeric index (even negative), change it and return
        modified. Otherwise returns None

        >>> Cmd.changepathindex('a.b', 0) is None
        True
        >>> Cmd.changepathindex('', 0) is None
        True
        >>> Cmd.changepathindex('a.1', -2)
        'a.-2'
        """
        if isinstance(path, StringTypes23):
            path = path.split('.')
        index = Cmd.pathindex(path)
        if index is None: return None
        else: return '.'.join(path[:-1] + ['%d'%new_index])

    def normpathindex(self, path):
        """Normalize path index if exists and is negative, so to become positive.
        Used setinfo.size, so works only for commands with setted this info.
        Returns normalized path or original if no index or index is positive.
        If index is out-of-set-size, returns None!
        """
        index = Cmd.pathindex(path)
        if index is None:
            return path
        elif index >= 0:
            if index >= self.setinfo.size: return None
            else: return path
        else:
            index = normnegindex(index, self.setinfo.size)
            if index is None: return None
            return Cmd.changepathindex(path, index)

    def matchpath(self, gpath):
        """Match me with glob-style path pattern

        >>> p = Cmd.create_cmd('<<c.f>>')
        >>> p.matchpath('c*')
        True
        >>> p.matchpath('*x')
        False
        >>> p.matchpath('c.f')
        True
        """
        normgpath = self.normpathindex(gpath)
        if normgpath: gpath = normgpath
        re_ = fnmatch.translate(gpath)
        cre = re.compile(re_)
        return bool(cre.match(self.jpath()))

    def setpath(self, path=None, prefix=None, suffix=None):
        """Change path with optional prefix (str|list|tuple),
        suffix (str|list|tuple). IF no path, current is used

        >>> p = Cmd.create_cmd('<<c.f>>')
        >>> p.path
        ['c', 'f']
        >>> p.setpath('', ('a','b'), 'x.y')
        ['a', 'b', 'c', 'f', 'x', 'y']
        >>> p.setpath(('a', 'b'))
        ['a', 'b']
        >>> p.setpath(prefix='x')
        ['x', 'a', 'b']
        >>> p.setpath('x.y.z', '', ['t'])
        ['x', 'y', 'z', 't']
        """
        if not path: path = self.path
        if not prefix: prefix = []
        if not suffix: suffix = []

        if isinstance(path, StringTypes23):
            path = path.split('.')
        if isinstance(suffix, StringTypes23):
            suffix = suffix.split('.')
        if isinstance(prefix, StringTypes23):
            prefix = prefix.split('.')
        self.path = list(prefix) + list(path) + list(suffix)
        return self.path

    def __hash__(self):
        """Generate key when object is used as key

        >>> d = dict()
        >>> d[Cmd.create_cmd('<<c.f>>')] = 123
        >>> d[Cmd.create_cmd('<<c.f>>')]
        123
        >>> d[Cmd.create_cmd('<<c.f, x>>')] = 321
        >>> d[Cmd.create_cmd('<<c.f,  x>>')]
        321
        >>> d[Cmd.create_cmd('<<c.f>>')]
        123
        >>> Cmd.create_cmd('<<c.f1>>') in d
        False
        """
        factors = (tuple(self.path), tuple(self.args), tuple(self.body))
        return hash(factors)

    def __eq__(self, oth):
        if isinstance(oth, Cmd):
            return self.path == oth.path
        elif isinstance(oth, StringTypes23):
            return self.jpath() == oth
        else:
            return False

    def hasarg(self, args):
        """Test existent of arg name

        >>> c = Cmd.create_cmd()
        >>> c.parse('<<c.sum, a: 1, b: 2>>')
        True
        >>> c.hasarg('a')
        True
        >>> c.hasarg('b')
        True
        >>> c.hasarg(('a', 'b'))
        True
        >>> c.hasarg(('a', 'b', 'x'))
        False
        >>> c.hasarg(('x', 'b'))
        False
        >>> c.hasarg('x')
        False
        """
        if isinstance(args, StringTypes23):
            args = [args]
        for arg in args:
            if not any(myarg[0]==arg for myarg in self.args):
                return False
        return True

    def getarg(self, args, default=None):
        """Returns value of named arg (or arg aliases, args may be list or str)

        >>> c = Cmd.create_cmd()
        >>> c.parse('<<c.sum, a: 1, b: 2>>')
        True
        >>> c.getarg('a')
        '1'
        >>> c.getarg(('aa', 'a'))
        '1'
        >>> c.getarg('x', default=10)
        10
        """
        if isinstance(args, StringTypes23):
            args = [args]
        for k,v in self.args:
            if k in args:
                return v
        return default

    def jpath(self, delim='.'):
        return delim.join(self.path)

    def parse(self, text):
        """Reset fields then parse text

        >>> Cmd.create_cmd('')
        Traceback (most recent call last):
            ...
        CmdError: mismatch form
        >>> c = Cmd.create_cmd()
        >>> c.parse('<c.sum>')
        Traceback (most recent call last):
            ...
        CmdError: mismatch form
        >>> c.parse('<<>>')
        Traceback (most recent call last):
            ...
        CmdError: empty path
        >>> c.parse('<<c.sum,,>>')
        Traceback (most recent call last):
            ...
        CmdError: missed arg
        >>> c.parse('<<c.sum, x!y:10>>')
        Traceback (most recent call last):
            ...
        CmdError: arg 'x!y' contains unallowed symbols
        >>> c.parse('<<c.sum, x.y:10>>') and c.body==[] \
                and c.args==[('x.y', '10')]
        True
        >>> c.parse('<<c.sum>>') and not c.ispaste and not c.isset
        True
        >>> c.parse('<<=c.sum.*>>') and c.text=='<<=c.sum.*>>' and c.ispaste \
                and c.isset and c.path==['c', 'sum', '*']
        True
        >>> c.parse('<<c.sum>>') and c.text=='<<c.sum>>' and not c.ispaste \
                and c.path==['c', 'sum'] and c.args==[] and c.body==[]
        True
        >>> c.parse('<<c.a sum, bbb, ddd>>') and c.text=='<<c.a sum, bbb, ddd>>' \
                and not c.ispaste and c.path==['c', 'a sum'] and c.args==[] \
                and c.body==['bbb', 'ddd']
        True
        >>> c.parse('<<c.sum, a:>>') and c.body==[] \
                and c.args==[('a', '')]
        True
        >>> c.parse('<<c.sum, a: 1, b: 2>>') and c.body==[] \
                and c.args==[('a', '1'), ('b', '2')]
        True
        >>> c.parse('<<c.sum, a:b:c>>') and c.body==[] \
                and c.args==[('a', 'b:c')]
        True
        >>> c.parse('<<c.sum, a::c>>') and c.body==[] \
                and c.args==[('a', ':c')]
        True
        >>> c.parse('<<c.sum, :a:b:c>>') and c.body==[] \
                and c.args==[('', 'a:b:c')]
        True
        >>> c.parse('<<c.sum, a::>>') and c.body==[] \
                and c.args==[('a', ':')]
        True
        >>> c.parse('<<c.sum, a:1, ccc, b:2, ddd>>') and c.body==['ccc', 'ddd'] \
                and c.args==[('a', '1'), ('b', '2')]
        True
        >>> c.parse('<<c.sum, a:\\,>>') and c.body==[] \
                and c.args==[('a', ',')]
        True
        >>> c.parse('<<c.sum, a:b c d>>') and c.body==[] \
                and c.args==[('a', 'b c d')]
        True
        >>> c.parse('<<c.sum, a\\:8000/>>') and c.body==['a:8000/'] \
                and c.args==[]
        True
        >>> c.parse('<<use, mnt:c, fmt:md, http\\://localhost\\:8000/cstd.md>>') \
                and c.args==[('mnt', 'c'), ('fmt', 'md')] \
                and c.body==['http://localhost:8000/cstd.md']
        True
        >>> c.parse('<<c.sum, a:\\:, xxx\\:yyy\\,>>') and c.body==['xxx:yyy,'] \
                and c.args==[('a', ':')]
        True
        >>> c.parse('<<c.sum, a:b, *:*>>') and c.body==[] \
                and c.args==[('a', 'b'), ('novars', True)]
        True
        >>> Cmd.syntax.pushsurr(['(', ')', '<<<', '>>>'])
        >>> c.parse('(use, mnt:c, fmt:md, http\\://localhost\\:8000/cstd.md)') \
                and c.args==[('mnt', 'c'), ('fmt', 'md')] \
                and c.body==['http://localhost:8000/cstd.md']
        True
        >>> Cmd.syntax.popsurr()
        """
        # denied in kw arg name
        _ArgNameDeniedSymbols = string.punctuation.replace('.', '')

        def _quote_text(txt):
            for i,q in enumerate(CMDQUOTE):
                txt = txt.replace(r'\%s'%q, '@Q%d@'%i)
            return txt
        def _unquote_text(txt):
            for i,q in enumerate(CMDQUOTE):
                txt = txt.replace('@Q%d@'%i, q)
            return txt

        self._reset()
        if not Cmd.syntax.istoken('cmddef', text) \
                and not Cmd.syntax.istoken('cmdsubst', text):
            raise CmdError('mismatch form')

        self.text = text
        text = Cmd.syntax.strip(text)

        text = _quote_text(text)
        tmp = [t.strip() for t in text.split(',')]
        pathpart, args = tmp[0], tmp[1:]
        if not pathpart:
            raise CmdError('empty path')

        if pathpart[0] == '=':
            self.path = pathpart[1:].split('.')
            self.ispaste = True
        else:
            self.path = pathpart.split('.')
            self.ispaste = False
        self.isset = '*' in self.path

        for arg in args:
            if not arg:
                raise CmdError('missed arg')
            tmp = [t.strip() for t in arg.split(':', 1)]
            tmplen = len(tmp)
            if tmplen == 1:
                tmp[0] = _unquote_text(tmp[0])
                self.body.append(tmp[0])
            elif tmplen == 2:
                # process argument
                if tmp[0] == '*':
                    if tmp[1] == '*':
                        self.args.append(('novars', True))
                    elif tmp[1].startswith('$'):
                        self.args.append(('varsdict', tmp[1][1:]))
                else:
                    if any(tmp0ch in _ArgNameDeniedSymbols for tmp0ch in tmp[0]):
                        raise CmdError("arg '%s' contains unallowed symbols"%tmp[0])
                    tmp[0] = _unquote_text(tmp[0])
                    tmp[1] = _unquote_text(tmp[1])
                    self.args.append((tmp[0], tmp[1]))
        return True

    def onsubargs(self, parser=None, name=None, value=None):
        return ((), dict(parser=parser, name=name, value=value))

    def ondefine(self, parser=None, chunktext=None):
        """Calling on define new chunk with this cmd.
        Should returns modified or original chunk text.
        If returns None in chunktext, adding is disable (skipped)
        """
        if parser:
            self.srcinfo.infile = parser.infile
        return ((), dict(parser=parser, chunktext=chunktext))

    def onpost(self, parser=None, flush=None):
        """Called on post-processing of input.
        parser is concrete Parser object, flush is flag - flushing to
        file is enabled
        """
        return ((), dict(parser=parser, flush=flush))

    def onpaste(self, parser=None, chunktext=None):
        """Called after extending text of command
        """
        return ((), dict(parser=parser, chunktext=chunktext))

################################################################################

class Chunk:
    """Base class for all chunk handlers, like 'c'
    """
    ## original text
    orig = None
    ## code text
    tangle = None
    ## all expanded
    isdone = None
    ## dependencies for this chunk (list of Cmd)
    deps = None
    ## ID of traversing session (for cycle detection)
    _walkid = None
    ## count of visiting (for cycle detection)
    _nvisits = None

    ## regexp for var. placeholders: '$...\b' or '${...}' or '$N' or '$-N' or '$*'
    _varplaceholders_re_ = r'\$({.+?}|\*|-?.+?\b)'
    _varplaceholders_re = re.compile(_varplaceholders_re_)

    def __init__(self, text=None):
        """Construct and if there is text, do some preparing

        >>> c = Chunk('')
        >>> c.isdone
        True
        >>> bool(c)
        False
        >>> c = Chunk('aaa')
        >>> c.isdone
        True
        >>> c.tangle
        'aaa'

        # TODO tangle will be '<<c.fun>>' but looks strange. May be warning?
        >>> c = Chunk('<<c.fun>>')
        >>> c.isdone
        True
        >>> c = Chunk('<<=c.fun>>')
        >>> c.isdone
        False
        """
        self.orig = text
        self._reset()

    def _reset(self):
        self.tangle = ''
        self.isdone = False
        self.deps = []
        self._walkid = 0
        self._nvisits = 0
        # update deps, isdone, tangle (if no deps, tangle is text) from self.orig
        if self.orig is not None:
            self.deps = self._finddeps(self.orig)
            if Chunk._isdone(self.orig):
                self.tangle = self.orig # i.e. = text
                self.isdone = True

    def __len__(self):
        return len(self.orig)

    @staticmethod
    def _subargs(text, parser=None, posargs=(), kwargs={}):
        """Substitute kwargs, posargs with their values. Arg in text should be
        prefixed with $. If there is arg novars=True, replaces arguments with it's names

        >>> Chunk._subargs('A text $a $b b c $a $c', kwargs=dict(a='AAA', b=9, x=10))
        'A text AAA 9 b c AAA $c'
        >>> Chunk._subargs('A text $a $b b c $a $c', kwargs=dict(a='AAA', b=9, x=10, novars=True))
        'A text a b b c a c'
        >>> Chunk._subargs('aaa $a')
        'aaa $a'
        >>> Chunk._subargs('Aaa $0 $1 b c $-1 $-2 $*', posargs=(10, 20))
        'Aaa 10 20 b c 20 10 1020'
        """
        def _varname(s):
            """Name of variable from it's placeholder in text -
            'xxx' -> 'xxx' and '{xxx}' -> 'xxx'

            >>> _varname('')
            ''
            >>> _varname('aa')
            'aa'
            >>> _varname('{aaa}')
            'aaa'
            """
            if s.startswith('{'):
                return s[1:-1]
            else:
                return s

        def __varvalue(varname, posargs, kwargs, novars, varsdict):
            """Value-replacer for var. name (placeholder)"""
            if novars: return varname
            if varname == '*': # TODO add '**' also? (to _varplaceholders_re_ too!)
                return posargs
                #return ''.join(str(a) for a in posargs)
            elif isint(varname):
                idx = normnegindex(int(varname), len(posargs))
                if idx is None: return varname
                else: return posargs[idx]
            elif varsdict:
                assert parser, "parser can't be None when varsdict is used"
                # order of var getting ("frame inheritance")
                return kwargs.get(varname, None) or \
                        parser.getvar(varname, varsdict, default=None)
            else:
                return kwargs.get(varname, None) or \
                        (parser.getvar(varname, default=None) if parser else None)

        def _varvalue(varname, posargs, kwargs, novars, varsdict):
            varvalue = __varvalue(varname, posargs, kwargs, novars, varsdict)
            if parser:
                varvalue = parser.raiseevent('subargs', parser=parser, name=varname,
                        value=varvalue)['value']
            if isinstance(varvalue, (list, tuple)): return ''.join(str(v) for v in varvalue)
            else: return varvalue

        novars = kwargs.get('novars', False)
        varsdict = kwargs.get('varsdict', None)
        # resolve '$...' values of kwargs
        for argname, argvalue in kwargs.items():
            argvalue = str(argvalue)
            if argvalue.startswith('$'):
                assert parser, "parser can't be None with arg reference"
                argvalue = parser.getvar(argvalue)
                kwargs[argname] = argvalue

        # substitute
        textvars = Chunk._varplaceholders_re.findall(text)
        for textvar in set(textvars):
            varname = _varname(textvar)
            #print 'Found textvar %s with name %s'%(textvar, varname)
            varvalue = _varvalue(varname, posargs, kwargs, novars, varsdict)
            #print 't: %s, n:%s, v:%s, novars=%s'%(textvar, varname, varvalue, novars)
            if varvalue is not None:
                text = text.replace('$%s'%textvar, str(varvalue))
            #print "So text is '%s'"%text
        return text

    def subargs(self, parser=None, posargs=(), kwargs={}):
        """Substitute arguments and set 'tangle' and 'isdone'

        >>> c = Chunk('aaa $a $b')
        >>> c.isdone
        False
        >>> c.subargs(kwargs=dict(a=1))
        False
        >>> c.subargs(kwargs=dict(b=2))
        True
        >>> c.tangle
        'aaa 1 2'
        >>> c = Chunk('aaa $a')
        >>> c.subargs()
        False
        >>> c.tangle
        'aaa $a'
        """
        self.tangle = Chunk._subargs(self.tangle or self.orig, parser=parser,
                posargs=posargs, kwargs=kwargs)
        return self.update_isdone()

    @staticmethod
    def _subcmd(text, path, content):
        """Substitute FIRST pasted cmd (has 'path') with 'content'

        >>> Chunk._subcmd('aaa <<=x.y, a:1, b:2>>', 'x.y', 'zzz')
        'aaa zzz'
        >>> Chunk._subcmd('aaa <<=x.yz>>', 'x.y', 'zzz')
        'aaa <<=x.yz>>'
        """
        return Cmd.syntax.subtokens('concrcmdsubst', content, text, count=1, path=path)

    def subcmd(self, path, content):
        """Substitute pasted cmd and set 'tangle' and 'isdone'

        >>> c = Chunk('aaa $a $b <<=x.y, z>>')
        >>> c.isdone
        False
        >>> c.subargs(kwargs=dict(a=1))
        False
        >>> c.subcmd('x.y', 'zzz')
        False
        >>> c.subargs(kwargs=dict(b=2))
        True
        >>> c.tangle
        'aaa 1 2 zzz'
        """
        self.tangle = Chunk._subcmd(self.tangle or self.orig, path, content)
        return self.update_isdone()

    @staticmethod
    def _isdone(text):
        """Check is text does not need more substitution

        >>> Chunk._isdone('')
        True
        >>> Chunk._isdone('A $a $b $c')
        False
        >>> Chunk._isdone('A $$ $')
        True
        >>> Chunk._isdone('<<aa>>')
        True
        >>> Chunk._isdone('<<=aa>>')
        False
        """
        if next(Cmd.syntax.findtokens('argsubst', text), UNDEFINED) is UNDEFINED \
                and next(Cmd.syntax.findtokens('cmdsubst', text), UNDEFINED) is UNDEFINED:
            return True
        else:
            return False

    def update_isdone(self):
        self.isdone = Chunk._isdone(self.tangle)
        return self.isdone

    @staticmethod
    def _finddeps(text):
        """Find dependencies in text

        >>> Chunk._finddeps('')
        []
        >>> Chunk._finddeps('aaa')
        []
        >>> Chunk._finddeps('<<c.fun>>')
        []
        >>> ['.'.join(d.path) for d in \
                Chunk._finddeps('aaa <<=c.fun1>> and <<=c.fun2, a:1,b:2,ccc>>')]
        ['c.fun1', 'c.fun2']
        >>> deps = Chunk._finddeps('   <<=c.fun1>> and <<=c.fun2, a:1,b:2,ccc>>')
        >>> deps[0].indent == '   '
        True
        >>> deps[1].indent == ''
        True
        """
        txtdeps = Cmd.syntax.findtokens('cmdsubst', text)
        result = []
        for txtdep in txtdeps:
            # each pasted cmd should have indent string, to indent tangled text later
            indent = indentstr(text, txtdep.start(0))
            result.append(Cmd.create_cmd(txtdep.group(0), indent=indent))
        return result

    def visit(self, walkid):
        if self._walkid != walkid:
            # new walk session
            self._walkid = walkid
            self._nvisits = 1
        else:
            # old walk session
            self._nvisits += 1
        return self._nvisits

################################################################################

class ChunkDictError(Exception): pass

class ChunkDict:
    """Dictionary of chunks, where key is Cmd
    """
    def __init__(self):
        self.chunks = OrderedDict()

    def __len__(self):
        return len(self.chunks)

    # XXX does not check cycles, do it explicitly
    def merge(self, othchunkdict, path=''):
        """Like dict update(), but merge under prefixed path. Cycles are not
        checked after merging, do it explicitly

        >>> cd1 = ChunkDict()
        >>> cd1.define_chunk(Cmd.create_cmd('<<c.sum>>'), Chunk('x + y'))
        True
        >>> cd2 = ChunkDict()
        >>> cd2.define_chunk(Cmd.create_cmd('<<c.abs>>'), Chunk('x + y'))
        True
        >>> cd1.merge(cd2, 'a.b')
        >>> Cmd.create_cmd('<<c.abs>>') in cd1.chunks
        False
        >>> Cmd.create_cmd('<<a.b.c.abs>>') in cd1.chunks
        True
        >>> cd3 = ChunkDict()
        >>> cd3.define_chunk(Cmd.create_cmd('<<c.sum>>'), Chunk('x + y'))
        True
        >>> cd1.merge(cd3)
        Traceback (most recent call last):
            ...
        ChunkDictError: 'c.sum' path already exists when merging
        >>> cd1.merge(cd3, 'x')
        """
        #print 'Try to merge %s'%', '.join(p.jpath() for p in othchunkdict.chunks.keys())
        for cmd, chunk in othchunkdict.chunks.items():
            cmd.setpath(prefix=path)
            if cmd in self.chunks:
                raise ChunkDictError("'%s' path already exists when merging" % \
                        cmd.jpath())
            self.chunks[cmd] = chunk

    def define_chunk(self, cmd, chunk):
        """Register chunk with name/header as cmd

        >>> cd = ChunkDict()
        >>> cd.define_chunk(Cmd.create_cmd('<<c.sum>>'), Chunk('x + y'))
        True
        >>> Cmd.create_cmd('<<c.sum>>') in cd.chunks
        True
        """
        self.chunks[cmd] = chunk
        return True

    def __askey(self, something):
        if isinstance(something, Cmd):
            return something
        elif isinstance(something, StringTypes23):
            cmd = Cmd.create_cmd(something)
            index = Cmd.pathindex(cmd.path)
            if index is None or index >= 0:
                # not indexed or index is positive
                return cmd
            else:
                # else cmd is with negative index, so do:
                # - find command (cmd0) with the same path but index 0
                # - cmd0 knows about set cmd1...cmdN and normalizes negative index
                # - returns command with normalized path
                try: cmd0,_ = self.getbypath(Cmd.changepathindex(cmd.path, 0)) # get xxx.0
                except KeyError: raise KeyError(cmd.jpath()) # no such command!
                return self.getbypath(cmd0.normpathindex(cmd.path))[0]
        else:
            return None

    def get_uniform_commands(self, name):
        """Returns registered commands instances which has class name 'name' or
        are it's successors - like Cmd.get_uniform_commands()
        """
        cmdcls = Cmd.get_uniform_commands(name)
        gpaths = [c.gpath for c in cmdcls]
        ret = []
        for gpath in gpaths:
            ret.extend(self.globpath(gpath))
        return ret

    def globpath(self, gpath, _onlypath=False):
        """Return keys for pattern 'gpath' - components
        may be '*' - match like glob. If '_onlypath', returns list of paths, not
        Cmd's (for tests purpose)

        >>> cd = ChunkDict()
        >>> cd.define_chunk(Cmd.create_cmd('<<c>>'), Chunk('a'))
        True
        >>> cd.define_chunk(Cmd.create_cmd('<<c.sum>>'), Chunk('a'))
        True
        >>> cd.define_chunk(Cmd.create_cmd('<<c.abs>>'), Chunk('a'))
        True
        >>> cd.define_chunk(Cmd.create_cmd('<<d.defs>>'), Chunk('a'))
        True
        >>> cd.globpath('c.sum', _onlypath=True)
        ['c.sum']
        >>> cd.globpath('*.sum', _onlypath=True)
        ['c.sum']
        >>> cd.globpath('c.*', _onlypath=True)
        ['c.sum', 'c.abs']
        >>> cd.globpath('*.*', _onlypath=True)
        ['c.sum', 'c.abs', 'd.defs']
        >>> cd.globpath('*.x', _onlypath=True)
        []
        >>> cd.globpath('*', _onlypath=True)
        ['c', 'c.sum', 'c.abs', 'd.defs']
        >>> cd.globpath('*.', _onlypath=True)
        []
        """
        found = []
        for cmd in self.chunks.keys():
            if cmd.matchpath(gpath):
                found.append(cmd)
        if _onlypath:
            return [f.jpath() for f in found]
        else:
            return found

    def getbypath(self, key):
        """key is dotted path or Cmd

        >>> cd = ChunkDict()
        >>> cd.define_chunk(Cmd.create_cmd('<<c.sum, a:1, b:2>>'), Chunk('x + y'))
        True
        >>> k,v = cd.getbypath('c.sum')
        >>> k == 'c.sum'
        True
        >>> v.orig == 'x + y'
        True
        >>> cd.getbypath('aaa')
        Traceback (most recent call last):
            ...
        KeyError: 'aaa'
        """
        _key = self.__askey(key)
        if _key is None:
            raise KeyError(key)
        else:
            for k,v in self.chunks.items():
                if k == _key:
                    return (k, v)
        raise KeyError(key)

    def getbykey(self, cmd):
        """Returns chunk by Cmd key"""
        return self.chunks[cmd]

    def keys(self, **attrs):
        """Returns Cmd (keys) matched by it's attrs (or all if no attrs)

        >>> cd = ChunkDict()
        >>> cd.define_chunk(Cmd.create_cmd('<<c.sum>>'), Chunk('x + y'))
        True
        >>> cd.define_chunk(Cmd.create_cmd('<<c.abs>>'), Chunk('x + y'))
        True
        >>> l = list(cd.keys(path=['c', 'sum']))
        >>> [c.jpath() for c in l]
        ['c.sum']
        """
        if attrs:
            for cmd in self.chunks.keys():
                if all(getattr(cmd, attr)==attrs[attr] for attr in attrs):
                    yield cmd
        else:
            for cmd in self.chunks.keys():
                yield cmd

    def __contains__(self, key):
        """Test of existent

        >>> cd = ChunkDict()
        >>> cd.define_chunk(Cmd.create_cmd('<<c.sum>>'), Chunk('x + y'))
        True
        >>> 'c.sum' in cd
        True
        """
        key = self.__askey(key)
        if key is None:
            return False
        else:
            return key in self.chunks

    # Seems that not work
    def check_cycle(self, cmd, walkid):
        """Check are any cycles, returns True if there are, False else
        """
        chunk = self.chunks[cmd]
        if chunk.visit(walkid) > 1:
            return True
        for dep in chunk.deps:
            if dep in self.chunks:
                if self.check_cycle(dep, walkid):
                    return True
        return False

    def check_cycles(self):
        """Check cycles in all registered chunks. If there are some cycles, raise
        ChunkDictError

        >>> cd = ChunkDict()
        >>> cd.define_chunk(Cmd.create_cmd('<<c.a>>'), Chunk('aaa <<=c.b>> bbb'))
        True
        >>> cd.check_cycles()
        >>> cd.define_chunk(Cmd.create_cmd('<<c.b>>'), Chunk('<<=c.a>>'))
        True
        >>> cd.check_cycles()
        Traceback (most recent call last):
            ...
        ChunkDictError: cyclic 'c.a'
        """
        for cmd in self.chunks.keys():
            walkid = random.randint(0,32768) #os.urandom(8)
            if self.check_cycle(cmd, walkid):
                raise ChunkDictError("cyclic '%s'"%cmd.jpath())

    def expand(self, path, visited=None, parser=None, posargs=(), kwargs={}):
        """Try to expand all '<<=...>>' holders

        >>> cd = ChunkDict()
        >>> cd.define_chunk(Cmd.create_cmd('<<c.a>>'), Chunk('aaa <<=c.b, d:end, x:10>> bbb'))
        True
        >>> cd.define_chunk(Cmd.create_cmd('<<c.b>>'), Chunk('<<=c.d, y:2>> $d'))
        True
        >>> cd.define_chunk(Cmd.create_cmd('<<c.d>>'), Chunk('xxx $x $y'))
        True
        >>> cd.expand('c.a')
        True
        >>> cd.getbypath('c.a')[1].tangle
        'aaa xxx 10 2 end bbb'

        >>> cd = ChunkDict()
        >>> cd.define_chunk(Cmd.create_cmd('<<c.a>>'), Chunk('aaa'))
        True
        >>> cd.define_chunk(Cmd.create_cmd('<<c.b>>'), Chunk('bbb'))
        True
        >>> cd.define_chunk(Cmd.create_cmd('<<c>>'), Chunk('ccc <<=c.*, join:\\,>> ddd'))
        True
        >>> cd.expand('c')
        True
        >>> cd.getbypath('c')[1].tangle
        'ccc aaa,bbb ddd'

        >>> cd = ChunkDict()
        >>> cd.define_chunk(Cmd.create_cmd('<<c.a>>'), Chunk('aaa <<=c.b>>'))
        True
        >>> cd.define_chunk(Cmd.create_cmd('<<c.b>>'), Chunk('bbb <<=c.a>>'))
        True
        >>> cd.define_chunk(Cmd.create_cmd('<<c>>'), Chunk('ccc <<=c.*, join:\\,>> ddd'))
        True
        >>> cd.expand('c') # doctest:+ELLIPSIS
        Traceback (most recent call last):
            ...
        ChunkDictError: cyclic ...
        """

        if visited is None:
            visited = []

        # normalize path with negative index first
        cmd, chunk = self.getbypath(path)

        jpath = cmd.jpath()
        if jpath in visited:
            raise ChunkDictError("cyclic '%s'"%jpath)

        visited.append(jpath)
        depsaredone = True
        for dep in chunk.deps:
            # over dependencies as Cmd (<<=dep>> - dep may be glob path)
            globpath = dep.jpath() # glob path or usual path
            joinkw = dep.getarg('join', '') # dep can have 'join' arg
            startkw = dep.getarg('start', '') # also 'start' arg
            endkw = dep.getarg('end', '') # also 'end' arg
            deps = self.globpath(globpath) # one or several Cmd's
            if not deps:
                raise KeyError(globpath)
            repls = [] # replace with joined items of this list (tangles of glob paths)
            for depcmd in deps:
                # how depend is registered in dict:
                deppath = depcmd.jpath()
                depchunk = self.getbykey(depcmd)
                depchunk._reset()
                _posargs = posargs if not dep.body else dep.body # not copy bcz won't change
                _kwargs = kwargs.copy()
                _kwargs.update(dep.args)
                #print '>', deppath, visited, parser, _posargs, _args
                if not self.expand(deppath, visited=visited, parser=parser, posargs=_posargs, kwargs=_kwargs):
                    # impossible to extend now, so skip this depend
                    depsaredone = False
                    continue

                # if dep is done or was sucessfully expanded, keep it in repls
                repls.append(startkw + depchunk.tangle + endkw)
                #print '>>', depchunk.tangle, repls, '<<'
            # join repls and substitute with it WITH INDENT
            repltext = indenttext(joinkw.join(repls), dep.indent)
            chunk.subcmd(globpath, repltext)
        # extend kwargs (total result is chunk.isdone)
        if parser:
            parser.trapevent(cmd, 'subargs')
        chunk.subargs(parser=parser, posargs=posargs, kwargs=kwargs)
        visited.pop()
        isdone = depsaredone and chunk.isdone
        if isdone and parser:
            chunk.tangle = parser.emitevent(cmd, 'paste', parser=parser,
                    chunktext=chunk.tangle)['chunktext']
        return isdone

################################################################################

class EventHandler:
    """Events handler - wrap event matching
    """
    ## dict of object attrs for matching
    params = None
    ## {func-name: func}
    helper_funcs = {}
    ## on*() - gets dict, returns possible changed dict
    handler_func = None

    def __init__(self, handler_func, **params):
        self.params = params.copy()
        self.handler_func = handler_func

    def __repr__(self):
        return "<EventHandler instance at 0x%X>"%id(self)

    def __eq__(self, oth):
        return self.params == oth.params

    def __hash__(self):
        return hash(tuple((k,v) for k,v in self.params.items()))

    def __getattr__(self, name):
        """Access params values as instance attribute
        >>> e = EventHandler(None, a=1, b=2)
        >>> e.a + e.b
        3
        """
        if name not in self.params: raise AttributeError
        try: return self.params.get(name)
        except: raise AttributeError(name)

    @staticmethod
    def getargspec(obj, event):
        """Returns arguments description like in inspect for event
        handler
        """
        m = getattr(obj, 'on'+event)
        return inspect.getargspec(m)

    def change_gpath(self, gpath='', prefix='', suffix=''):
        """If there is gpath in params, change it value, otherwise nothing to do

        >>> e = EventHandler(None, a=1, b=2)
        >>> e.change_gpath('xxx')
        >>> 'gpath' in e.params
        False
        >>> e = EventHandler(None, a=1, b=2, gpath='a.b')
        >>> e.change_gpath(prefix='0')
        >>> e.gpath
        '0.a.b'
        >>> e.change_gpath(gpath='x.y')
        >>> e.gpath
        'x.y'
        >>> e.change_gpath(gpath='', prefix='.a', suffix='.b.c.')
        >>> e.gpath
        'a.x.y.b.c'
        """
        if 'gpath' in self.params:
            if not gpath: gpath = self.params['gpath']
            p = (p for p in (prefix.strip('.'), gpath.strip('.'), suffix.strip('.')) if p)
            self.params['gpath'] = '.'.join(p)

    def canhandle(self, obj, event):
        """Test can this event handler handle this event for this object

        >>> c = Cmd.create_cmd()
        >>> c.parse('<<c.sum, x.y:10>>')
        True
        >>> e = EventHandler(None, gpath='c.*', event='no-such-event')
        >>> e.canhandle(c, 'define')
        False
        >>> e = EventHandler(None, gpath='c.*', event='define')
        >>> e.canhandle(c, 'define')
        True
        >>> e = EventHandler(None, id=id(c), event='define')
        >>> e.canhandle(c, 'define')
        True
        >>> e = EventHandler(None, id=id(c), event='define')
        >>> e.canhandle(None, 'define')
        False
        >>> e = EventHandler(None, id=id(c), xxx=0, event='define')
        >>> e.canhandle(c, 'define')
        False
        """
        for parname, parval in self.params.items():
            if parname == 'classname':
                m = parval == obj.__class__.__name__
            elif parname == 'id':
                m = parval == id(obj)
            elif parname == 'hash':
                m = parval == hash(obj)
            elif parname == 'gpath':
                assert isinstance(obj, Cmd) # only Cmd has .gpath
                m = obj.matchpath(parval)
            elif parname == 'event':
                m = parval == event
            else:
                m = parval == getattr(obj, parname, UNDEFINED)
            if not m:
                return False
        return True

    @staticmethod
    def register_func(name, func):
        """Register function (not class/instance) to process some event.
        """
        EventHandler.helper_funcs[name] = func

    @staticmethod
    def getfunc(funcname):
        """Return helper func"""
        try: return EventHandler.helper_funcs[funcname]
        except KeyError: raise ValueError("no such helper function '%s'"%funcname)

################################################################################

class VfileInfo:
    """Meta information about Vfile
    """
    ## format (extension, like '.md')
    fmt = None
    ## name of file
    name = None
    ## mode bits (see os.chmod())
    mode = None
    ## access time
    atime = None
    ## modified time
    mtime = None

    def __init__(self, **kw):
        for n,v in kw.items():
            setattr(self, n, v)
        self._normalize()

    def _normalize(self):
        if self.fmt and not self.fmt.startswith('.'):
            self.fmt = '.' + self.fmt

    def update(self, othinfo):
        for k in ('fmt', 'name', 'mode', 'atime', 'mtime'):
            v = getattr(othinfo, k)
            if v is not None: setattr(self, k, v)
        self._normalize()

    @staticmethod
    def mkst_time(timetuple):
        """Make seconds from time tuple (Y,MON,D,H,M,S)
        """
        d = datetime.datetime(*timetuple)
        return calendar.timegm(d.timetuple())

################################################################################

class Vfile:
    """URL/FS-path mapped to local FS

    Ex, create tmp local file (and write into), map it, open, read:

    Create:
    >>> ntmp = None; vf = None
    >>> fdtmp,ntmp = tempfile.mkstemp()
    >>> utmp = path2url(ntmp, 'file')
    >>> buf = b'Hello there!'
    >>> os.write(fdtmp, buf) == len(buf)
    True
    >>> os.close(fdtmp)

    Now map:
    >>> vf = Vfile.create_vfile(utmp)
    >>> vf.__class__ is FSURLfile
    True
    >>> vf.map() # doctest:+ELLIPSIS
    <...>
    >>> vf.local_uri.fspath.lower() == ntmp.lower()
    True

    Opened is independent (file descriptor is duplicated), so it possible
    to open/close/open several times:
    >>> vf.open().close() # doctest:+ELLIPSIS
    <...>

    Open and read:
    >>> rbuf = vf.open().read()
    >>> len(rbuf) == len(buf)
    True
    >>> rbuf == buf
    True
    >>> if vf: del vf
    >>> os.remove(ntmp)

    Now try zip file:
    >>> ntmp = None; vf = None
    >>> ntmp = os.path.join(tempfile.gettempdir(), str(random.random()).replace('.','_')) + '.zip'
    >>> fname = 'a/b/c.md'
    >>> utmp = path2url(ntmp, 'zip', fragment=fname)
    >>> zip = zipfile.ZipFile(ntmp, 'w')
    >>> zip.writestr(fname, buf)
    >>> zip.close()
    >>> vf = Vfile.create_vfile(utmp)
    >>> vf.__class__ is ZIPfile
    True
    >>> rbuf = vf.map().open().read()
    >>> rbuf == buf
    True
    >>> os.remove(ntmp)
    >>> if vf: del vf
    """
    descr = ''
    ## regexp for URL that can fetch
    scheme = None
    ## remote-execution security hole when True! FIXME: NOT USED YET
    unsafe = False

    #_tmpfiles = [] # all tmp files' paths to be deleted
    vfiles = [] # all registered Vfile vfiles

    ## Uri to original object
    orig_uri = None
    ## Uri to mapped object
    local_uri = None
    ## VfileInfo object
    info = None
    ## tmp file descriptor
    fd = None
    ## tmp file object (is set after opening)
    fileobj = None
    ## True if local FS file is mapped to local FS
    fakemap = False

    def __init__(self, url):
        self.orig_uri = Uri(url)

    def __del__(self):
        self.close()
        self.unmap()
        if not self.fakemap:
            self.remove()

    #def __getattr__(self, attr):
        #"""All unknown attributes will be got from self.fileobj"""
        #if not self.fileobj: raise ValueError('Vfile was not opened')
        #return getattr(self.fileobj, attrname)

    @staticmethod
    def register(vfile):
        Vfile.vfiles.append(vfile)

    @staticmethod
    def create_vfile(url):
        """Vfile factory

        >>> vf = Vfile.create_vfile('http://aaa.bbb.com/x/y/z.md')
        >>> vf.__class__ is HTTPfile
        True
        >>> vf.obtaininfo().fmt == '.md'
        True
        >>> vf.orig_uri.name == 'z.md'
        True
        >>> vf = Vfile.create_vfile('file:///aaa.bbb.com/x/y/z.md')
        >>> vf.__class__ is FSURLfile
        True
        >>> vf = Vfile.create_vfile('/a/b/c/z.md')
        >>> vf.__class__ is FSfile
        True
        >>> vf.orig_uri.name == 'z.md'
        True
        """
        for cls in Vfile.vfiles:
            if re.match(cls.scheme, url, re.I):
                return cls(url)
        else:
            raise ValueError("Unsupported fetching scheme for '%s'"%url)

    #@staticmethod
    #def deltmpfiles():
    #    """Closes and deletes all temporary files"""
    #    for fd, fpath in Vfile._tmpfiles:
    #        try:
    #            # close file descriptor
    #            os.close(fd)
    #            # then remove file from disk
    #            os.chmod(fpath, stat.S_IWRITE)
    #            os.remove(fpath)
    #        except: pass
    #    Vfile._tmpfiles = []

    def obtaininfo(self):
        """Obtains VfileInfo for self.orig_url. It's limited if orig_url is not local FS-path.
        May be overriden
        """
        if self.orig_uri.islocal():
            name = self.orig_uri.name
            fmt = os.path.splitext(name)[1]
            stat = os.stat(self.orig_uri.fspath)
            return VfileInfo(fmt=fmt, name=name, mode=stat.st_mode, atime=stat.st_atime, mtime=stat.st_mtime)
        else:
            urlpath = urlsplit(self.orig_uri.url)[2]
            name = os.path.split(urlpath)[1]
            fmt = os.path.splitext(name)[1]
            return VfileInfo(fmt=fmt, name=name)

    def map(self, parser=None):
        """Maps URL to local FS-path after fetching object. If fetch() returns None,
        maps to the same object as orig_uri
        """
        mapped = self.fetch(parser)
        if not mapped:
            self.fakemap = True
            self.local_uri = self.orig_uri
            self.info = self.obtaininfo()
            self.fd = os.open(self.local_uri.fspath, os.O_RDWR|_O_BINARY)
        else:
            self.fakemap = False
            info, buffer = mapped
            self.info = self.obtaininfo()
            if info:
                self.info.update(info)
            self.fd, fpath = tempfile.mkstemp(suffix=self.info.fmt, prefix=self.info.name + '.')
            #Vfile._tmpfiles.append((self.fd, fpath))
            if self.info.mode:
                os.chmod(fpath, self.info.mode)
            if self.info.atime and self.info.mtime:
                os.utime(fpath, (self.info.atime, self.info.mtime))
            os.write(self.fd, buffer)
            os.lseek(self.fd, 0, os.SEEK_SET)
            self.local_uri = Uri(fpath)
        return self

    def unmap(self):
        """Close self.fd. If early was call close(), it's needless"""
        if self.fileobj:
            raise ValueError('Vfile is busy')
        if self.fd:
            os.close(self.fd)
            self.fd = None
        return self

    def remove(self):
        """VERY DANGEROUSE: if mapping is local file to local file, this method will
        delete original file!"""
        if self.local_uri:
            os.chmod(self.local_uri.fspath, stat.S_IWRITE)
            os.remove(self.local_uri.fspath)
        return self

    def fetch(self, parser=None):
        """Should return pair (vfileInfo, buffer), where vfileinfo can be None,
        buffer is readed bytes from original resource. If returns None, then
        resource is treated as local and no mapping is needed.
        parser may be None (in tests)
        """
        raise NotImplementedError

    def isopen(self):
        """To check that is opened already"""
        return bool(self.fileobj)

    # lightweight emulation of file:

    def open(self, mode='rb', *args):
        """Opens file - set self.fileobj from self.fd (got early by map())
        and becames like file-object
        """
        if not self.fd: raise ValueError('Vfile was not mapped')
        if self.fileobj: raise ValueError('Vfile is already opened')
        self.fileobj = os.fdopen(os.dup(self.fd), mode, *args)
        return self

    def seek(self, *args):
        if not self.fileobj: raise ValueError('Vfile is not opened')
        return self.fileobj.seek(*args)

    def tell(self):
        if not self.fileobj: raise ValueError('Vfile is not opened')
        return self.fileobj.tell()

    def read(self, *args):
        if not self.fileobj: raise ValueError('Vfile is not opened')
        return self.fileobj.read(*args)

    def write(self, *args):
        if not self.fileobj: raise ValueError('Vfile is not opened')
        return self.fileobj.write(*args)

    def close(self):
        if self.fileobj:
            self.fileobj.close()
            self.fileobj = None
        return self
#atexit.register(Vfile.deltmpfiles)

################################################################################

class Uri:
    """URI for some filename or file-object
    """
    ## path in FS (if exists in FS)
    fspath = ''
    ## URL to object (in Web or FS)
    url = ''
    ## short name
    name = ''

    @staticmethod
    def matchurl(url, scheme=UNDEFINED, path=UNDEFINED, netloc=UNDEFINED, fragment=UNDEFINED):
        """Match URL with scheme, path, netloc, fragment and that url is looks like URL
        (not FS path). Returns UriMatchResult with failed attribute (list of failed
        components, may be 'url' - not URL even)

        >>> 'url' in Uri.matchurl('c:/a/b').failed
        True
        >>> 'url' in Uri.matchurl('/c/a/b').failed
        True
        >>> not Uri.matchurl('http://c/a/b').failed == True
        True
        >>> not Uri.matchurl('zip://c/a/b').failed == True
        True
        >>> not Uri.matchurl('zip://c/a/b', scheme='zip').failed == True
        True
        >>> 'netloc' in Uri.matchurl('zip://c/a/b', netloc='localhost').failed
        True
        >>> not Uri.matchurl('file:///c/a/b', scheme='file').failed == True
        True
        """
        class UriMatchResult:
            """Result of matching. Test on boolean or see .failed attr"""
            def __init__(self, f=None): self.failed = f or []

        failed = [] # which components were failed
        def _match_comp(master, value):
            if master is not UNDEFINED and value.lower() != master.lower():
                return False
            else:
                return True
        a = urlsplit(url)
        if len(a.scheme) < 2: failed.append('url')
        else:
            if not _match_comp(scheme, a.scheme): failed.append('scheme')
            if not _match_comp(path, a.path): failed.append('path')
            if not _match_comp(netloc, a.netloc): failed.append('netloc')
            if not _match_comp(fragment, a.fragment): failed.append('fragment')
        return UriMatchResult(failed)

    def __init__(self, file):
        """file may be string filename or file-object

        >>> Uri('http://localhost/a/b/c').url == 'http://localhost/a/b/c'
        True
        >>> tmpdir = os.path.normpath(tempfile.gettempdir())
        >>> str(Uri('http://sub.aaa.com/my'))
        "Uri(fspath='', url='http://sub.aaa.com/my', name='my')"
        >>> str(Uri('http://sub.aaa.com/my/path.htm?q1=1&q2=2'))
        "Uri(fspath='', url='http://sub.aaa.com/my/path.htm?q1=1&q2=2', name='path.htm')"

        # Try 'file:///<TMPDIR>'; may faults in splitdrive()
        >>> u = Uri(tmpdir)
        >>> os.path.normcase(u.fspath) == os.path.normcase(tmpdir)
        True
        >>> u.name == os.path.split(tmpdir)[1]
        True
        >>> u.url.startswith('file:///')
        True

        # The same but without 'file://'
        >>> u = Uri(tmpdir)
        >>> os.path.normcase(u.fspath) == os.path.normcase(tmpdir)
        True
        >>> u.name == os.path.split(tmpdir)[1]
        True
        """
        try:
            if isinstance(file, StringTypes23):
                m = Uri.matchurl(file, scheme='file')
                if not m.failed:
                    # it's 'file://' URL
                    file = url2path(file)
                elif 'scheme' in m.failed:
                    # it's URL with another scheme
                    self.fspath = ''
                    self.url = file
                    self.name = os.path.split(urlparse(self.url).path)[1]
                    return
                self.fspath = os.path.abspath(file)
                self.url = path2url(self.fspath, 'file')
                self.name = os.path.split(self.fspath)[1]
                return
            elif isinstance(file, Vfile):
                self.fspath = file.orig_uri.fspath
                self.url = file.orig_uri.url
                self.name = file.orig_uri.name
                return
            else:
                url = getattr(file, 'url', '')
                if url:
                    self.fspath = ''
                    self.url = url
                    self.name = os.path.split(urlparse(self.url).path)[1]
                    return
                else:
                    name = getattr(file, 'name', '')
                    # check open(file.name).fileno() == file.fileno() - i.e. in
                    # current dir.
                    if name:
                        absname = os.path.abspath(name)
                        if os.path.exists(absname):
                            with open(absname, 'r') as checkfp:
                                # XXX in Python docs it's Unix func. but exists in Win too
                                if os.path.sameopenfile(file.fileno(), checkfp.fileno()):
                                    self.fspath = absname
                                    self.url = path2url(self.fspath, 'file')
                                    self.name = os.path.split(self.fspath)[1]
                                    return
        except: pass
        raise ValueError("Can not convert '%s' to Uri object"%file)

    def withbase(self, base):
        """Returns new URL string from self but with new base address

        >>> u = Uri('http://sub.aaa.com/my')
        >>> u.withbase('')
        'http://sub.aaa.com/my'
        >>> u.withbase('ftp://a.b.c/')
        'ftp://a.b.c/my'
        >>> u = Uri('http://sub.aaa.com/x/y/z.htm')
        >>> u.withbase('ftp://a.b.c/')
        'ftp://a.b.c/x/y/z.htm'
        """
        if not base: return self.url
        else:
            assert bool(self.url)
            up = urlsplit(base)
            path = urlsplit(self.url).path
            up = up._replace(path=path)
            return urlunsplit(up)

    def getmoniker(self):
        """Return some unique name for system"""
        def _url2str(url):
            if not url: return ''
            if len(url) < 64: return url
            else: return url[:32] + ' ... ' + url[-32:]
        # return FS-path or URL-as-str or name or empty-name
        return self.fspath or _url2str(self.url) or self.name or 'unknown'

    def islocal(self):
        """Returns if resource if local on machine
        """
        if self.fspath: return True
        elif self.url: return False
        else: raise RuntimeError('Wrong Uri instance')

    def __repr__(self):
        return "%s(fspath='%s', url='%s', name='%s')"%\
                (self.__class__.__name__, self.fspath, self.url, self.name)

################################################################################

class Token:
    text = ''
    start = -1
    end = -1

    def __init__(self, text, start=-1, end=-1):
        self.text = text
        self.start = start
        self.end = end
    def __repr__(self):
        return '<%s at %d...%d: %s>' % (self.__class__.__name__, self.start, self.end, self.text)

class EndToken(Token): pass

class CmdToken(Token): pass

class InlCodeToken(Token):
    @staticmethod
    def linearize(text, nl=('\n',), space=' '):
        """Convert new-lines symbols|text-fragments (nl) to space

        >>> InlCodeToken.linearize('aaa#bbb!ccc', nl=('#', '!'))
        'aaa bbb ccc'
        >>> InlCodeToken.linearize('##aaa##bbb###ccc#', nl='#', space='-')
        'aaa-bbb-ccc'
        >>> InlCodeToken.linearize('@LFaaa@CRbbb@LFccc@LF@LF', nl=('@CR', '@LF'), space='-')
        'aaa-bbb-ccc'
        >>> InlCodeToken.linearize('aaa\\n\\nbbb')
        'aaa bbb'
        """
        if isinstance(nl, (list, tuple)):
            nl = '|'.join('(%s)'%n for n in nl)
        re_ = '(%s)+'%nl
        cre_ = re.compile(re_)
        return cre_.sub(space, text).strip(space)

class BlkCodeToken(Token):
    def jointoken(self, token):
        """Join token to existent text"""
        self.text = self.text.rstrip('\n') + '\n' + token.text.lstrip('\n')
        self.end = token.end
        return self

################################################################################

class LineExp:
    """One line expression (parsable and callable later)
    """
    ## delimiter between expressions (';' in 'exp0; exp1;...')
    delim = None
    ## sequence of callable objects
    script = None
    ## resolver of functions (class with getfunc())
    resolver = None
    ## skip this arg's names in single-arg call (don't apply in wrapped func)
    stdargs = None

    def __init__(self, script=[], delim=';'):
        """Init with another callable objects list (script)
        """
        self.delim = delim
        self.reset()
        self.script.extend(script)
        self.resolver = None
        self.stdargs = ()

    def setcontext(self, resolver, stdargs=UNDEFINED, rec=False):
        """stdargs - not apllyed args in single-arg func call.
        Usually stdargs is mandatory but when importing of parser is doing
        (and merging of event handlers sure) it's not necessary.
        If rec (recoursivly) - set resolver to all LineExp scripts in self.
        """
        self.resolver = resolver
        if rec:
            for scr in self.script:
                if isinstance(scr, LineExp): scr.setcontext(resolver, rec=rec)
        if stdargs is not UNDEFINED:
            self.stdargs = stdargs

    def reset(self):
        self.script = []

    def __len__(self): return len(self.script)

    def extend(self, script):
        self.script.extend(script)

    def __call__(self, *args, **kwargs):
        """Pipe-call"""
        if self.resolver is None or self.stdargs is None:
            raise ValueError("resolver or stdargs are not set")
        _args = args[:]; _kwargs = kwargs.copy()
        for s in self.script:
            if isinstance(s, FuncInfo):
                _args, _kwargs = self._call_funcinfo(s, *_args, **_kwargs)
            else:
                _args, _kwargs = s(*_args, **_kwargs)
        return (_args, _kwargs)

    def _call_funcinfo(self, funcinfo, *args, **kwargs):
        """Returns callable - standard for NanoLP 'do.EVENT' expression.
        'funcinfo' is returned by parselnexp()
        """
        funcname = funcinfo.funcname
        posargspec = funcinfo.posargs
        kwargspec = funcinfo.kwargs
        # convert '-xx' to 'x'
        kwargspec = {(k[1:] if k.startswith('-') else k):v for k,v in kwargspec.items()}
        func = self.resolver.getfunc(funcname)
        # find all '$..' from kwargs
        vars = [a for a in posargspec if a.startswith('$') and a[1:] in kwargs]
        if len(vars) > 1: raise ValueError('only one selector allowed')
        elif len(vars) == 1:
            # single-arg func
            def resolver(k):
                try: return kwargs.get(k)
                except: return k
            varname = vars[0][1:]
            posargspec, kwargspec = subargs(resolver, *posargspec, **kwargspec)
            args, kwargs = subargs(resolver, *args, **kwargs)
            kwargs = {k:v for k,v in kwargs.items() if k not in tuple(self.stdargs)+(varname,)}
            singlearg = functools.partial(func, *posargspec, **kwargspec)(*args, **kwargs)
            kwargs[varname] = singlearg
            return (args, kwargs)
        else:
            # multiple-arg func
            return functools.partial(func, *posargspec, **kwargspec)(*args, **kwarg)

    def parse(self, text):
        """text is one line expression like 'func1 -opt.. arg..; func2..'
        """
        exps = (t.strip() for t in text.split(self.delim))
        for exp in exps:
            s = parselnexp(exp)
            self.script.append(s)
        return self

################################################################################

class ParserError(Exception): pass

## trap for events from another program sites
EventTrap = namedtuple('EventTrap', ['obj', 'event'])

class Parser:
    """Parse doc file"""
    ## description of parser class
    descr = ''
    ## all registered parsers
    parsers = []

    ## ChunkDict object
    chunkdict = None
    ## error locator object
    errloc = None
    ## {dict-name: vars-dict} of this parser
    vars = None
    ## list of EventHandler's
    handlers = None
    ## output directory (for saved files, used by FileCmd, RefsFile)
    outdir = ''
    ## input file name or file-object
    infile = ''
    ## LP instance (XXX may be None)
    engine = None
    ## parent parser (which included from)
    parent = None
    ## catcher of events {event:EventTrap}
    eventtraps = None

    ## supported file extensions by concrete parser class
    ext = ()
    ## used when parse by concrete parser class
    surr = ('<<', '>>')
    ## params from config file (mandatory)
    config_params = ['ext:strlist', 'surr:strlist']

    def __init__(self, engine=None, parent=None):
        """For doctests engine can be None"""
        self._reset()
        self.engine = engine
        self.parent = parent

    def _reset(self):
        self.chunkdict = ChunkDict()
        self.errloc = ErrorLocator()
        self.vars = {ANONDICTNAME:{}}
        self.handlers = []
        Cmd.syntax.setsurr(self.surr)
        self.outdir = ''
        self.infile = ''
        self.eventtraps = {}

    @staticmethod
    def register(p):
        """Register new parser"""
        Parser.parsers.append(p)

    @classmethod
    def getcfgparams(class_):
        """Return names of config params"""
        return (s.split(':')[0] for s in class_.config_params)

    @classmethod
    def config(class_, name, value):
        """Configure concrete parser class"""
        def compilparam(s):
            arr = s.split(':')
            name, type = arr if len(arr)==2 else (arr[0], 'str')
            typefun = getattr(Cfgfile, type, None)
            assert typefun is not None
            return (name, typefun)
        paramsdict = dict(compilparam(p) for p in class_.config_params)
        if name not in paramsdict.keys():
            raise KeyError("Parameter '%s' is out of expected" % name)
        value = paramsdict[name](value)
        setattr(class_, name, value)

    def getrootparser(self):
        """Find root parser (first parent)"""
        p = self
        while p.parent is not None:
            p = p.parent
        return p

    #def getindir(self):
        #"""Return input directory"""
        # better but not tested:
        #dirname = ''
        #if self.infile:
            ## if there is input file, try to use it dir as input dir
            #uri = Uri(self.infile)
            #if uri.islocal() and os.path.exists(uri.fspath):
                ## if input file is local FS and exists
                #return os.path.dirname(uri.fspath)
        #return os.getcwd()
        # orig:
        #if self.infile:
        #    uri = Uri(self.infile)
        #    if uri.islocal():
        #        return os.path.dirname(uri.fspath)
        #return os.getcwd()

    def setupoutdir(self, infile):
        """Find and setup output directory: from command line option or root parser
        or from input file, or current dir. Setup self.outdir!
        """
        self.outdir = ''
        if self.engine and self.engine.outdir:
            # is set as command line option
            outdir = self.engine.outdir
        else:
            rootparser = self.getrootparser()
            if rootparser.outdir:
                # may be set already in root parser
                outdir = rootparser.outdir
            else:
                # else try to determine from infile, if it's in FS
                uri = Uri(infile)
                if uri.islocal():
                    # if infile is FS local
                    outdir = os.path.dirname(uri.fspath)
                else:
                    # else will be current dir
                    outdir = os.getcwd()
        if not os.path.exists(outdir):
            raise ParserError("Output directory '%s' does not exists"%outdir)
        else:
            self.outdir = outdir
            return outdir

    def ensureinput(self, path):
        """Return full path/URL from path/URL. If path is relative path (FS),
        try to treat it as in the same dir. as input directory of parser (with
        already parsed input file!). If path is relative but URL, return abs.
        URL (see absurl()).
        If it's FS path (not URL) and not exists, returns None
        """
        uri = Uri(self.infile)

        if not Uri.matchurl(path).failed:
            # if path is URL return it
            return path
        else:
            # path is not abs. URL, may be rel. URL or FS-path (rel. or abs.)
            if os.path.isabs(path):
                # path is abs., so treats it as FS abs. path
                return path
            else:
                # some rel. path, may be rel. URL or rel. FS-path
                if not uri.islocal():
                    # input file is URL (non-local), so convert rel. path
                    # to abs. URL (based on URL of input file)
                    return absurl(uri.url, path)
                else:
                    # input file is in FS
                    infile_dir = os.path.dirname(uri.fspath)
                    p = os.path.join(infile_dir, path)
                    if os.path.exists(p):
                        # such path exists in directory of input file
                        return p
                    else:
                        # if no such file, try to find it in parent parser input dir
                        p = self.parent.ensureinput(path) if self.parent else None
                        if p:
                            # exists in parent input directory
                            return p
                        else:
                            # not found in parent input directory, try in current
                            p = os.path.join(os.getcwd(), path)
                            if os.path.exists(p):
                                # exists in current directory
                                return p
        return None

    def tokens(self, text):
        """Abstract: Iterator over tokens"""
        raise NotImplementedError

    @classmethod
    def findlines(class_, text, delim='\n'):
        """Split text to lines coordinates (coords of line-breaking symbols).
        delim is one symbol or list/tuple of symbols as line delimiters.
        If text of file is not usual text, this method should be reloaded!

        >>> text = '@aaa bbb!ccc!ddd@'
        >>> Parser.findlines(text, delim=('!', '@'))
        [0, 8, 12, 16]
        >>> text = '\\naaa bbb\\nccc\\nddd\\n'
        >>> Parser.findlines(text)
        [0, 8, 12, 16]
        """
        lncoords = []
        if isinstance(delim, StringTypes23):
            splitter_re_ = re.escape(delim)
        else:
            splitter_re_ = '(%s)' % '|'.join(re.escape(s) for s in delim)
        splitter_re = re.compile(splitter_re_)
        for m in splitter_re.finditer(text):
            lncoords.append(m.start(0))
        return lncoords

    def readfile(self, file):
        """Returns content of file"""
        # FIXME improve
        return fix_crlf(file.read().decode('utf8'))
        #if isinstance(file, StringTypes23):
            #return fread23(file)
        #else:
            #return fix_crlf(bytestostr23(file.read()))

    @staticmethod
    def _prepare_cmd(cmdtext, bodytexts):
        """Prepare list of pairs (cmdtext, cmdbody) from cmdtext (path) and
        body texts

        >>> Parser._prepare_cmd('c.a', [])
        [('c.a', '')]
        >>> Parser._prepare_cmd('c.a', ['b'])
        [('c.a', 'b')]
        >>> Parser._prepare_cmd('c.a', ['b1', 'b2'])
        [('c.a.0', 'b1'), ('c.a.1', 'b2')]
        """
        bodytextlen = len(bodytexts)
        if bodytextlen == 0:
            return [(cmdtext, '')]
        elif bodytextlen == 1:
            return [(cmdtext, bodytexts[0])]
        elif bodytextlen > 1:
            return [('%s.%s'%(cmdtext, ci), b) for ci,b in enumerate(bodytexts)]

    def _instance_handlers(self, obj):
        """There are 2 kind of handlers: class-based, created with <<on.CLASS...>>
        and instance-based, created with <<cmd, do.EVENT:...>>. Class-based are
        created by OnCmd.__ondefine__(). Before emit event, instance handlers should
        be created and added first
        """
        handlers = []
        if isinstance(obj, Cmd):
            cmd = obj
            if not hasattr(cmd, '__ondefine__'):
                # add handler from do.EVENTx attributes, but only if
                # no __ondefine__ method, which means 'No any handling!'
                classname = cmd.__class__.__name__
                for argname, argvalue in cmd.args:
                    if argname.startswith('do.'):
                        # some handler
                        event = argname[3:] # 3==len('do.')
                        params = dict(classname=classname, event=event)
                        if event == 'paste':
                            params['gpath'] = cmd.jpath()
                        else:
                            params['id'] = id(cmd)
                        functext = argvalue
                        func = LineExp().parse(functext)
                        func.setcontext(resolver=self,
                                stdargs=EventHandler.getargspec(obj, event).args)
                        handlers.append(EventHandler(func, **params))
        return handlers

    def trapevent(self, obj, event):
        """Set trap (catcher) for event. Event can be raised from deep code levels to
        some event trap without knowledge about event handler object (obj attr.)
        """
        self.eventtraps[event] = EventTrap(obj=obj, event=event)

    def raiseevent(self, event, **args):
        """Raise event to event trap, setted somewhere. If exists, returns
        result of usual event handler(-s), otherwise - None"""
        if event in self.eventtraps:
            trap = self.eventtraps[event]
            ret = self.emitevent(trap.obj, trap.event, **args)
            del self.eventtraps[event]
            return ret
        else:
            return args

    def emitevent(self, obj, event, **args):
        """Call all handlers and object onXXX() if no __onXXX__().
        Otherwise call only __onXXX__()
        """
        methname = 'on%s'%event; __methname__ = '__%s__'%methname
        meth = getattr(obj.__class__, methname, None)
        __meth__ = getattr(obj, __methname__, None)
        if __meth__:
            # if there is hidden for handlers callback - call it only
            outposargs, outkwargs = __meth__(**args)
            return outkwargs # ignore pos. args
        elif not meth:
            # XXX is really need to have onXXX() ?
            # else if no usual callback - raise error
            raise AttributeError("'%s' should have '%s' method" % \
                    (obj.__class__.__name__, methname))
        else:
            # add instance handlers
            self.updatehandlers(self._instance_handlers(obj))
            # get responsible handlers for this obj and event
            handlers = [meth]
            handlers.extend(h.handler_func for h in self.handlers if h.canhandle(obj, event))
            do = LineExp(handlers)
            do.setcontext(resolver=self,
                    stdargs=EventHandler.getargspec(obj, event).args)
            outposargs, outkwargs = do(obj, **args)
            return outkwargs # ignore pos. args

    def define_chunk(self, cmdtext, bodytexts):
        """Define new chunk with cmdtext (path) and list of body texts

        >>> p = Parser()
        >>> p.define_chunk('c.a', ['b1', 'b2', 'b3'])
        >>> p.chunkdict.globpath('c.a.*', _onlypath=True)
        ['c.a.0', 'c.a.1', 'c.a.2']
        >>> p.chunkdict.getbypath('c.a.0')[1].orig
        'b1'
        >>> p.chunkdict.getbypath('c.a.2')[1].orig
        'b3'
        >>> p.chunkdict.globpath('c.a.2', _onlypath=True)
        ['c.a.2']
        >>> p.chunkdict.getbypath('c.a.-1')[1].orig
        'b3'
        >>> p.chunkdict.getbypath('c.a.-2')[1].orig
        'b2'
        >>> p.chunkdict.getbypath('c.a.-3')[1].orig
        'b1'
        >>> p.chunkdict.globpath('c.a.-1', _onlypath=True)
        ['c.a.2']
        """
        p = Parser._prepare_cmd(cmdtext, bodytexts)
        cmdsetinfo = Cmd.SetInfo()
        nbodies = 0
        for cmdtext, bodytext in p:
            cmd = Cmd.create_cmd(cmdtext, setinfo=cmdsetinfo)
            bodytext = self.emitevent(cmd, 'define', parser=self, chunktext=bodytext)['chunktext']
            if bodytext is not None:
                self.chunkdict.define_chunk(cmd, Chunk(bodytext))
            nbodies += 1
        cmdsetinfo.size = nbodies

    @staticmethod
    def create_parser(engine, path='', fmt='', parent=None):
        """General parser factory. path is FS-path or URL (but fmt is mandatory
        is this case!), parent - is parent parser, which included from (None for root
        parser)
        """
        if fmt:
            ext = '.' + fmt.strip('.').lower()
        elif path:
            ext = os.path.splitext(path)[1].lower()
        # find concrete parser class
        for cls in Parser.parsers:
            if ext in cls.ext:
                break
        else:
            raise ParserError('Unsupported file type')
        # return its instance
        return cls(engine=engine, parent=parent)

    def parsefile(self, file, flush=True):
        """General usage method for processing input file.
        Flag flush enable writing files with <<file.*, FSPATH>> command.
        """
        self._reset()
        if isinstance(file, StringTypes23):
            file = Vfile.create_vfile(file).map(self).open()
            return self.parsefile(file, flush=flush)
            #file = self._safe_create_vfile(file)
            #if not file: return self
            #else: return self.parsefile(file, flush=flush)
        else:
            # treats as file-object
            self.infile = file

        # determine self.outdir
        self.setupoutdir(file)

        filetext = self.readfile(file)
        self.errloc.config(filename=Uri(self.infile).getmoniker(), lncoords=self.findlines(filetext))
        # parse file content
        self._parse(filetext)
        self.chunkdict.check_cycles()
        # post-process of commands
        for cmd in self.chunkdict.keys():
            self.emitevent(cmd, 'post', parser=self, flush=flush)
        return self

    # XXX does not reset parser state like parsefile()
    def _parse(self, text):
        """Parse with error info providing"""
        try:
            return self.__parse(text)
        except Exception as x:
            tb = sys.exc_info()[2]
            errlocation = self.errloc.locate()
            if not errlocation:
                raise
            else:
                file,line = errlocation
                reraise23(x, "[%s, %d] %s"%(file, line+1, str(x)), tb)

    # XXX does not check cycles, do it explicitly
    def __parse(self, text):
        """Parse text. Don't forget to check cycles after!
        """
        def _iscmddef_right(cmdtext, bodytexts):
            """Check if custom cmdtext definition is right or not.
            Does not use lex BUT SYNTAX for checking"""
            if not bodytexts and not Cmd.isregistered(cmdtext):
                # not registered cmd. but definition of new with EMPTY body!
                # So it's incorrect cmd. definition!
                return False
            else:
                return True

        self.errloc.reset()
        tokens = self.tokens(text)
        #print '\n\n|', getattr(self.infile, 'url', ''), '|', tokens, '\n\n'
        state = 'start' # start|cmd|body
        # EndToken will terminate tokens ALWAYS
        notokens = all(isinstance(t, EndToken) for t in tokens)
        if notokens:
            return 0

        self.errloc.config(pos=tokens[0].start)
        itok = 0
        cmdtext = ''; bodytexts = []
        # 'continue' repeat processing of token which finished previous token
        # definition collecting
        while True:
            token = tokens[itok]
            self.errloc.config(pos=token.start)
            if state == 'start':
                if isinstance(token, CmdToken):
                    cmdtext = token.text
                    state = 'cmd'
                else:
                    raise ParserError('syntax error: expected CmdToken')
            elif state == 'cmd':
                if isinstance(token, (InlCodeToken, BlkCodeToken)):
                    bodytexts.append(token.text)
                    state = 'body'
                elif isinstance(token, CmdToken):
                    if _iscmddef_right(cmdtext, bodytexts):
                        self.define_chunk(cmdtext, bodytexts) # bodytexts is []
                    state = 'start'
                    cmdtext = ''; bodytexts = []
                    continue
                elif isinstance(token, EndToken):
                    if _iscmddef_right(cmdtext, bodytexts):
                        self.define_chunk(cmdtext, bodytexts) # bodytexts is []
                    break
                else:
                    raise ParserError('syntax error: expected InlCodeToken or BlkCodeToken')
            elif state == 'body':
                if isinstance(token, (InlCodeToken, BlkCodeToken)):
                    bodytexts.append(token.text)
                elif isinstance(token, CmdToken):
                    if _iscmddef_right(cmdtext, bodytexts):
                        self.define_chunk(cmdtext, bodytexts)
                    state = 'start'
                    cmdtext = ''; bodytexts = []
                    continue
                elif isinstance(token, EndToken):
                    if _iscmddef_right(cmdtext, bodytexts):
                        self.define_chunk(cmdtext, bodytexts)
                    break
            itok += 1
        #print [c.jpath() for c in list(self.chunkdict.keys())]
        return len(self.chunkdict)

    def expand(self, path, *posargs, **kwargs):
        return self.chunkdict.expand(path, visited=None, parser=self,
                posargs=posargs, kwargs=kwargs)

    def updatevars(self, dictname, varsdict):
        """Add new vars dict under dictname
        """
        if not dictname: dictname = ANONDICTNAME
        if dictname in self.vars:
            # this dict already exists
            self.vars[dictname].update(varsdict)
        else:
            # no such dict yet
            self.vars[dictname] = varsdict.copy()

    def updatehandlers(self, handlers):
        """Add new event handlers"""
        self.handlers.extend(handlers)
        self.handlers = list(set(self.handlers)) # make unique handlers list

    def getvar(self, varname, dictname=UNDEFINED, default=UNDEFINED):
        """Get var value from dict (if dictname is used), args no mean,
        instead of containing of 'default'
        """
        #print '+++++++ Try to resolve var %s of dict %s'%(varname, dictname)
        if dictname is UNDEFINED:
            # dictname is not used, so get it from varname
            lastdot = varname.rfind('.')
            if lastdot != -1:
                # there are dots in varname
                dictname = varname[:lastdot]
                varname = varname[lastdot+1:]
            else:
                # no dots in varname - it's from anon dict
                varname = varname
                dictname = ANONDICTNAME
        # get value from dict (or default)
        if default is not UNDEFINED:
            return self.vars.get(dictname, {}).get(varname, default)
        else:
            return self.vars[dictname][varname]

    def getfunc(self, funcname):
        # XXX getfunc - resolver interface for LineExp (for unification, no use of
        # EventHandler directly)
        return EventHandler.getfunc(funcname)

    def _mergehandlers(self, othparser, path=''):
        """Merge handlers from another parser
        """
        handlers = othparser.handlers[:]
        for h in handlers:
            h.change_gpath(prefix=path)
        self.handlers.extend(handlers)

    def _mergevars(self, othparser, path=''):
        """Merge vars dictionaries with vars of othparser. They names
        will be prefixed with path. Inheritance is supported: othparser
        vars will be reloaded by itself vars

        >>> p0 = Parser()
        >>> p0.updatevars('', {'v1':1, 'v2':2})
        >>> p0.updatevars('d1', {'v1':10, 'v2':20})
        >>> p0.getvar('v1'), p0.getvar('v2')
        (1, 2)
        >>> p0.getvar('d1.v1'), p0.getvar('d1.v2')
        (10, 20)

        >>> p1 = Parser()
        >>> p1.updatevars('', {'v1':1, 'v2':2})
        >>> p1.updatevars('d1', {'v1':10, 'v2':20})
        >>> p1.getvar('v1'), p1.getvar('v2')
        (1, 2)

        >>> p2 = Parser()
        >>> p2.updatevars('', {'v1':100, 'v2':200, 'v3':300})
        >>> p2.updatevars('d1', {'v1':1000, 'v2':2000, 'v3':3000})
        >>> p2.getvar('v1'), p2.getvar('v2'), p2.getvar('v3')
        (100, 200, 300)
        >>> p2.getvar('d1.v1'), p2.getvar('d1.v2'), p2.getvar('d1.v3')
        (1000, 2000, 3000)

        >>> p0._mergevars(p2)
        >>> p0.getvar('v1'), p0.getvar('v2'), p0.getvar('v3'), p0.getvar('d1.v1'), p0.getvar('d1.v3')
        (1, 2, 300, 10, 3000)

        p1 is unmodified:
        >>> p1.getvar('v1'), p1.getvar('v2'), p0.getvar('d1.v1'), p1.getvar('d1.v2')
        (1, 2, 10, 20)

        But no such var in p1:
        >>> p1.getvar('d1.v3')
        Traceback (most recent call last):
            ...
        KeyError: 'v3'

        >>> p1._mergevars(p2, 'x')
        >>> p1.getvar('v1'), p1.getvar('v2'), p1.getvar('d1.v1'), p1.getvar('d1.v2')
        (1, 2, 10, 20)
        >>> p1.getvar('v3')
        Traceback (most recent call last):
            ...
        KeyError: 'v3'
        >>> p1.getvar('d1.v3')
        Traceback (most recent call last):
            ...
        KeyError: 'v3'
        >>> p1.getvar('x.v3'), p1.getvar('x.d1.v3')
        (300, 3000)
        """
        for dictname, vars in othparser.vars.items():
            if path:
                # if there is path, imported dicts will have new names
                newdictname = '.'.join((path, dictname))
                if dictname == ANONDICTNAME:
                    # if import anon. dict with new path, it's be==path, i.e.
                    # $v == $anon.v, but the same with new path: $path.v
                    newdictname = path
            else:
                # if no path, amm other var. dicts will be with the same names
                newdictname = dictname
            if newdictname in self.vars:
                # there is such dict (under newdictname sure)
                myvars = self.vars[newdictname]
                for varname, varvalue in vars.items():
                    if varname not in myvars:
                        # import only unique names (inverse inheritance)
                        myvars[varname] = varvalue
            else:
                self.vars[newdictname] = vars.copy()

    def importparser(self, othparser, path=''):
        """Does importing of one parsed file (result of parsing is in othparser)
        with self
        """
        self.chunkdict.merge(othparser.chunkdict, path)
        self.chunkdict.check_cycles()
        self._mergevars(othparser, path)
        self._mergehandlers(othparser, path)

################################################################################

class Cfgfile(dict):
    """Config. file (rc-format) loader and parser
    """
    ## loaded file path
    filename = None

    ## config file param convert-functions:
    @staticmethod
    def strlist(value):
        """Convert string value as 'a,b,c...' to list of strings"""
        res = [s.strip() for s in value.split(',')]
        if all(not s for s in res): return []
        else: return res

    str = str
    int = int
    float = float

    def load(self, filename):
        self.filename = filename
        with open(self.filename, "rt") as ifile:
            for line in ifile:
                line = line.strip()
                if not line or line.startswith('#'): continue
                k, v = [s.strip() for s in line.split('=')]
                self[k] = v

################################################################################

class Urlcfgfile:
    """URL fetchers configuration file"""
    ## loaded file path
    filename = None
    ## ConfigParser instance
    _cfgp = None

    def __check_perm(self):
        """Check permissions security. If exists, return False on insecure
        mode, True on secure; if does not exist, return None"""
        if os.path.exists(self.filename):
            mode = os.stat(self.filename).st_mode
            if (0x180&mode) == 0x180:
                return True
            else:
                return False
        else:
            return None

    def urlopts(self, url):
        """If url matchs some from config. file, returns dictionary
        of it's options. If not matched, or no config. data in the file,
        returns None
        """
        if not self._cfgp:
            return None
        for sect in self._cfgp.sections():
            if re.search(sect, url):
                return dict(self._cfgp.items(sect))
        return None

    def load(self, filename):
        self.filename = filename
        # check permissions, if need, try to correct
        ckperm = self.__check_perm()
        if ckperm is None: return
        elif ckperm is False:
            warnings.warn("Wrong permissions on '%s', should be 0600. Correcting now..." % \
                    self.filename, warnings.UserWarning)
            try:
                os.chmod(self.filename, 0x180)
                if self.__check_perm() is not True: raise Exception()
            except:
                raise RuntimeError("Can not correct permissions of '' to 0666"%self.filename)
        cfgp = configparser.ConfigParser(allow_no_value=True)
        if cfgp.read(self.filename):
            self._cfgp = cfgp

################################################################################

class ErrorLocator:
    """Used to locate parsing error: what file and where in the file
    error occurs
    """
    ## parsed file name
    filename = None
    ## positions of lines: coords of its line-breaking symbol
    lncoords = None
    ## position in text; must be set before locate() call
    pos = None

    def __init__(self):
        self.filename = ''
        self.lncoords = []

    def config(self, filename=None, lncoords=None, pos=None):
        """Set current context, lncoords is the list of line coordinates

        >>> l = ErrorLocator()
        >>> l.config('file', [50, 20, 10, 0, 4])
        >>> l.lncoords
        [0, 4, 10, 20, 50]
        >>> l.config(pos=10)
        >>> l.pos
        10
        """
        if filename is not None:
            self.filename = filename
        if lncoords is not None:
            lncoords.sort()
            self.lncoords = lncoords
        if pos is not None:
            self.pos = pos

    def reset(self):
        """Opposite to config(), after call, locate() w/o pos arg returns None"""
        self.pos = None

    def locate(self, pos=None, default=True):
        """Get current context for pos symbol position in
        file text, if pos is None, self.pos is used

        >>> l = ErrorLocator()
        >>> l.locate(12, default=False) is None
        True
        >>> l.locate(12, default=True)
        ('<str>', 0)
        >>> l.config('file', [0, 30, 20, 10, 55])
        >>> l.locate(12)
        ('file', 2)
        >>> l.config(pos=1)
        >>> l.locate()
        ('file', 1)
        """
        if pos is None: pos = self.pos

        if self.filename and self.lncoords and pos is not None:
            return (self.filename, self._findline(pos))
        else:
            return ('<str>', 0) if default else None 

    def _findline(self, pos):
        """Find line number for this text position

        >>> l = ErrorLocator()
        >>> l.config('file', [0, 30, 20, 10, 55])
        >>> l._findline(0)
        0
        >>> l._findline(1)
        1
        >>> l._findline(10)
        1
        >>> l._findline(19)
        2
        >>> l._findline(30)
        3
        >>> l._findline(31)
        4
        >>> l._findline(55)
        4
        >>> l._findline(56)
        5
        >>> l._findline(100)
        5
        """
        for ln, lncoord in enumerate(self.lncoords):
            if pos <= lncoord:
                return ln
        return ln+1

################################################################################

class Lp:
    """Engine"""
    ## config file loader (dict)
    cfgfile = None
    ## url config. file loader
    urlcfgfile = None
    ## quiet mode, no console I/O
    quiet = False
    ## output directory (cmdline option, if not used then is '')
    outdir = ''

    def __init__(self, cfgfile='lprc', urlcfgfile='lpurlrc', quiet=False, outdir=''):
        self.cfgfile = Cfgfile()
        self.urlcfgfile = Urlcfgfile()
        self.quiet = quiet
        self.outdir = outdir
        # load configuration from cfgfile (abs. path or in current dir)
        cfgfile = os.path.abspath(cfgfile)
        self.cfgfile.load(cfgfile) # config file name
        for parser_class in Parser.parsers:
            cfgparser_class = parser_class.__name__.upper() # name of class in cfg file
            # obtain config values
            for param in parser_class.getcfgparams():
                cfgparam = '%s_%s' % (cfgparser_class, param.upper())
                parser_class.config(param, self.cfgfile[cfgparam])
        # load URL configuration from urlcfgfile (abs. path or in current dir)
        urlcfgfile = os.path.abspath(urlcfgfile)
        self.urlcfgfile.load(urlcfgfile) # config file name
