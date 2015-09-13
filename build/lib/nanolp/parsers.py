# Parsers
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

import re
import zipfile
import itertools
import xml.sax as sax
import xml.sax.saxutils as saxutils
import nanolp.core as core

class MDParser(core.Parser):
    """Markdown parser

    >>> text = \
    'Some text <<c.fun1>> `fun1-body1` and `fun2-body2` then\\n' \
    '<<c.fun2>> `fun2-body`'
    >>> p = MDParser()
    >>> p._parse(text)
    3
    >>> p.chunkdict.globpath('c.fun1.*', _onlypath=True)
    ['c.fun1.0', 'c.fun1.1']
    >>> p.chunkdict.globpath('c.fun2', _onlypath=True)
    ['c.fun2']
    >>> p.chunkdict.getbypath('c.fun1.0')[1].orig
    'fun1-body1'
    >>> p.chunkdict.getbypath('c.fun1.0')[1].tangle
    'fun1-body1'
    >>> p.chunkdict.getbypath('c.fun2')[1].tangle
    'fun2-body'
    >>> text = '<<c.f>> `x` and <<c.f1>> `x`'
    >>> p = MDParser()
    >>> p._parse(text)
    2
    >>> p.chunkdict.getbypath('c.f')[1].orig
    'x'
    >>> p.chunkdict.getbypath('c.f1')[1].orig
    'x'

    Another text, only command name and end of text then:
    >>> p._reset()
    >>> p._parse('Some text <<c.fun>> `x`')
    1
    >>> p.chunkdict.getbypath('c.fun')[0].jpath()
    'c.fun'
    >>> p.chunkdict.getbypath('c.fun')[1].orig
    'x'
    """

    descr = 'Markdown/MultiMarkdown'
    ext = ('.md',)

    def __init__(self, engine=None, parent=None):
        core.Parser.__init__(self, engine, parent)

    def tokens(self, text):
        """Returns tokens

        >>> text = \
        'Example of Literate Programming in Markdown\\n' \
        '===========================================\\n\\n' \
        \
        'Code 1\\n' \
        '------\\n\\n' \
        \
        'Test if variable is negative looks like <<c.isneg>>: `if a < 0`.\\n' \
        'So, we can write absolute function <<c.fun>>:\\n\\n' \
        \
        '    def fun(x):\\n' \
        '        <<=c.isneg,a:v>>:\\n' \
        '            a += 100\\n' \
        '            return -a\\n\\n' \
        \
        'And <<c.sum>>:\\n\\n' \
        \
        '    def sum(x, y):\\n' \
        '        return x+y\\n\\n' \
        \
        'not code\\n' \
        'not code\\n\\n' \
         \
        'Lalalalalalal\\n' \
        'Lalalalalalal\\n'
        >>> p = MDParser()
        >>> toks = p.tokens(text)
        >>> [tok.__class__.__name__ for tok in toks]
        ['CmdToken', 'InlCodeToken', 'CmdToken', 'BlkCodeToken', 'CmdToken', 'BlkCodeToken', 'EndToken']
        >>> toks[0].text
        'c.isneg'
        >>> toks[1].text
        'if a < 0'
        >>> toks[2].text
        'c.fun'
        >>> toks[3].text.startswith('def fun')
        True
        >>> toks[3].text.endswith('return -a')
        True
        """
        # left padding fragment of code-block
        indents = (4*' ', '\t') # possible padding
        indents = '|'.join(re.escape(s) for s in indents)

        _inlcode_re = r'`([^`]+)`'
        _blkcode_re = r'^\n(?P<code>((%s)(.*?)\n|\n)+)$' % indents
        _blkcode_lstrip_re = '^(%s)' % indents

        inlcode_re = re.compile(_inlcode_re)
        blkcode_re = re.compile(_blkcode_re, re.MULTILINE)
        blkcode_lstrip_re = re.compile(_blkcode_lstrip_re, re.MULTILINE)

        cmds = core.Cmd.syntax.findtokens('cmddef', text)
        inlcodes = inlcode_re.finditer(text)
        blkcodes = blkcode_re.finditer(text)

        tokens = []

        for m in cmds:
            token = core.CmdToken(m.group(1), m.start(0), m.end(0))
            tokens.append(token)
        for m in inlcodes:
            tokentext = core.InlCodeToken.linearize(m.group(1))
            token = core.InlCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)
        for m in blkcodes:
            # find each block and replace first left indent with ''
            tokentext = m.group('code').strip('\n')
            tokentext = blkcode_lstrip_re.sub('', tokentext)
            token = core.BlkCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)

        tokens.sort(key=lambda tok: tok.start)
        tokens.append(core.EndToken(None))
        return tokens
core.Parser.register(MDParser)

################################################################################

class CreoleParser(core.Parser):
    descr = 'Creole'
    ext = ('.creole', '.cre', '.crl')

    def __init__(self, engine=None, parent=None):
        core.Parser.__init__(self, engine, parent)

    def tokens(self, text):
        """Returns tokens

        >>> text = \
        '= Example of Literate Programming in Creole =\\n' \
        \
        '== Code 1 ==\\n' \
        \
        'Test if variable is negative looks like <<c.isneg>>: {{{if a < 0}}}.\\n' \
        'So, we can write absolute function <<c.fun>>:\\n\\n' \
        '{{{\\n' \
        '    def fun(x):\\n' \
        '        <<=c.isneg,a:v>>:\\n' \
        '            a += 100\\n' \
        '            return -a }}}\\n\\n' \
        \
        'And <<c.sum>>:\\n\\n' \
        \
        '{{{    def sum(x, y):\\n' \
        '        return x+y }}}\\n\\n' \
        \
        'not code\\n' \
        'not code\\n\\n' \
         \
        'Lalalalalalal\\n' \
        'Lalalalalalal\\n'
        >>> p = CreoleParser()
        >>> toks = p.tokens(text)
        >>> [tok.__class__.__name__ for tok in toks]
        ['CmdToken', 'BlkCodeToken', 'CmdToken', 'BlkCodeToken', 'CmdToken', 'BlkCodeToken', 'EndToken']
        >>> toks[0].text
        'c.isneg'
        >>> toks[1].text
        'if a < 0'
        >>> toks[2].text
        'c.fun'
        >>> toks[3].text.startswith('    def fun')
        True
        >>> toks[3].text.endswith('return -a')
        True
        """

        # XXX Only block chunks, inline and block Creole chunks are the same.
        # In real Creole distinguish block|inline chunks, but it's not
        # valuable for LP
        _blkcode_re = r'{{{\n*(?P<code>.*?)[\ \n]*}}}'

        blkcode_re = re.compile(_blkcode_re, re.DOTALL|re.MULTILINE)

        cmds = core.Cmd.syntax.findtokens('cmddef', text)
        blkcodes = blkcode_re.finditer(text)

        tokens = []

        for m in cmds:
            token = core.CmdToken(m.group(1), m.start(0), m.end(0))
            tokens.append(token)
        for m in blkcodes:
            # find each block and replace first left indent with ''
            tokentext = m.group('code')
            token = core.BlkCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)

        tokens.sort(key=lambda tok: tok.start)
        tokens.append(core.EndToken(None))
        return tokens
core.Parser.register(CreoleParser)

################################################################################

class RSTParser(core.Parser):
    """ReStructuredText parser"""
    descr = 'ReStructuredText'
    ext = ('.rst', '.rest', '.restr')

    def __init__(self, engine=None, parent=None):
        core.Parser.__init__(self, engine, parent)

    def tokens(self, text):
        """Returns tokens

        >>> text = \
        'Example of Literate Programming in ReSt\\n' \
        '===========================================\\n\\n' \
        \
        'Code 1\\n' \
        '------\\n\\n' \
        \
        'Test if variable is negative looks like <<c.isneg>>: ``if a < 0``.\\n' \
        'So, we can write absolute function <<c.fun>>::\\n\\n' \
        \
        '    def fun(x):\\n' \
        '        <<=c.isneg,a:v>>:\\n' \
        '            a += 100\\n' \
        '            return -a\\n\\n' \
        \
        'And <<c.sum>>n\\n' \
        '::\\n\\n' \
        \
        '    def sum(x, y):\\n\\n' \
        \
        '        return x+y\\n\\n' \
        '    x += 1'
        >>> p = RSTParser()
        >>> toks = p.tokens(text)
        >>> [tok.__class__.__name__ for tok in toks]
        ['CmdToken', 'InlCodeToken', 'CmdToken', 'BlkCodeToken', 'CmdToken', 'BlkCodeToken', 'EndToken']
        >>> toks[0].text
        'c.isneg'
        >>> toks[1].text
        'if a < 0'
        >>> toks[2].text
        'c.fun'
        >>> toks[3].text.startswith('def fun')
        True
        >>> toks[3].text.endswith('        return -a')
        True
        >>> toks[5].text.startswith('def sum')
        True
        >>> toks[5].text.endswith('x += 1')
        True
        """

        _inlcode_re = r'``([^`]+)``'
        _blkcode_re = r'::\n\n(?P<code>.*?)(?:$|(?:\n\n[^ \t]+))'

        inlcode_re = re.compile(_inlcode_re)
        blkcode_re = re.compile(_blkcode_re, re.DOTALL)

        cmds = core.Cmd.syntax.findtokens('cmddef', text)
        inlcodes = inlcode_re.finditer(text)
        blkcodes = blkcode_re.finditer(text)

        tokens = []

        for m in cmds:
            token = core.CmdToken(m.group(1), m.start(0), m.end(0))
            tokens.append(token)
        for m in inlcodes:
            tokentext = core.InlCodeToken.linearize(m.group(1))
            token = core.InlCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)
        for m in blkcodes:
            # find each block and replace first left indent with ''
            tokentext = m.group('code').strip('\n')
            tokentext = core.deltextindent(tokentext)
            token = core.BlkCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)

        tokens.sort(key=lambda tok: tok.start)
        tokens.append(core.EndToken(None))
        return tokens
core.Parser.register(RSTParser)

################################################################################

class Txt2TagsParser(core.Parser):
    """txt2tags Parser"""
    descr = 'Txt2Tags'
    ext = ('.t2t',)

    def __init__(self, engine=None, parent=None):
        core.Parser.__init__(self, engine, parent)

    def tokens(self, text):
        """Returns tokens

        >>> text = \
        '= Example of Literate Programming in Txt2Tags =\\n' \
        \
        '== Code 1 ==\\n' \
        \
        'Test if variable is negative looks like <<c.isneg>>: ``if a < 0``.\\n' \
        'So, we can write absolute function <<c.fun>>\\n' \
        '```\\n' \
        '    def fun(x):\\n' \
        '        <<=c.isneg,a:v>>:\\n' \
        '            a += 100\\n' \
        '            return -a\\n\\n' \
        '```\\n' \
        'And <<c.sum>>\\n' \
        '```\\n' \
        '    def sum(x, y):\\n\\n' \
        \
        '        return x+y\\n\\n' \
        '    x += 1\\n' \
        '```\\n' \
        'Last chunk is <<c.run>>\\n' \
        '``` $ ls -F1'
        >>> p = Txt2TagsParser()
        >>> toks = p.tokens(text)
        >>> [tok.__class__.__name__ for tok in toks]
        ['CmdToken', 'InlCodeToken', 'CmdToken', 'BlkCodeToken', 'CmdToken', 'BlkCodeToken', 'CmdToken', 'BlkCodeToken', 'EndToken']
        >>> toks[0].text
        'c.isneg'
        >>> toks[1].text
        'if a < 0'
        >>> toks[2].text
        'c.fun'
        >>> toks[3].text.startswith('def fun')
        True
        >>> toks[3].text.endswith('        return -a')
        True
        >>> toks[5].text.startswith('def sum')
        True
        >>> toks[5].text.endswith('x += 1')
        True
        >>> toks[7].text
        '$ ls -F1'
        """

        _inlcode_re = r'``([^\n`]+)``'
        _blkcode_re1 = r'(?:\n|^)```(?P<code>[^\n]+)(?:\n|$)'
        _blkcode_re2 = r'(?:\n|^)```\n+(?P<code>.*?)\n```(?:\n|$)'

        inlcode_re = re.compile(_inlcode_re)
        blkcode_re1 = re.compile(_blkcode_re1, re.DOTALL)
        blkcode_re2 = re.compile(_blkcode_re2, re.DOTALL)

        cmds = core.Cmd.syntax.findtokens('cmddef', text)
        inlcodes = inlcode_re.finditer(text)
        blkcodes = itertools.chain(blkcode_re1.finditer(text), blkcode_re2.finditer(text))

        tokens = []

        for m in cmds:
            token = core.CmdToken(m.group(1), m.start(0), m.end(0))
            tokens.append(token)
        for m in inlcodes:
            tokentext = core.InlCodeToken.linearize(m.group(1))
            token = core.InlCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)
        for m in blkcodes:
            # find each block and replace first left indent with ''
            tokentext = m.group('code').strip('\n')
            tokentext = core.deltextindent(tokentext)
            token = core.BlkCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)

        tokens.sort(key=lambda tok: tok.start)
        tokens.append(core.EndToken(None))
        return tokens
core.Parser.register(Txt2TagsParser)

################################################################################

class AsciiDocParser(core.Parser):
    """AsciiDoc Parser"""
    descr = 'AsciiDoc'
    ext = ('.asc', '.ascii', '.a2d')

    def __init__(self, engine=None, parent=None):
        core.Parser.__init__(self, engine, parent)

    def tokens(self, text):
        """Returns tokens

        >>> text = \
        'Example of Literate Programming in Asciidoc\\n' \
        '===========================================\\n\\n' \
        \
        'Code 1\\n' \
        '------\\n\\n' \
        \
        'Test if variable is negative looks like <<c.isneg>>: +if a < 0+.\\n' \
        'So, we can write absolute function <<c.fun>>\\n' \
        '[source, python]\\n' \
        '----\\n' \
        '    def fun(x):\\n' \
        '        <<=c.isneg,a:v>>:\\n' \
        '            a += 100\\n' \
        '            return -a\\n\\n' \
        '----\\n\\n' \
        'And <<c.sum>>\\n\\n' \
        '----\\n' \
        '    def sum(x, y):\\n\\n' \
        \
        '        return x+y\\n\\n' \
        '    x += 1\\n' \
        '----'
        >>> p = AsciiDocParser()
        >>> toks = p.tokens(text)
        >>> [tok.__class__.__name__ for tok in toks]
        ['CmdToken', 'InlCodeToken', 'CmdToken', 'BlkCodeToken', 'CmdToken', 'BlkCodeToken', 'EndToken']
        >>> toks[0].text
        'c.isneg'
        >>> toks[1].text
        'if a < 0'
        >>> toks[2].text
        'c.fun'
        >>> toks[3].text.startswith('def fun')
        True
        >>> toks[3].text.endswith('        return -a')
        True
        >>> toks[5].text.startswith('def sum')
        True
        >>> toks[5].text.endswith('x += 1')
        True
        """

        _inlcode_re = r'\+([^\n\+]+)\+'
        _blkcode_re = r'(?:\[source[^]]*?]\n|\n\n)-{4,}(?P<code>.*?)\n-{4,}'

        inlcode_re = re.compile(_inlcode_re)
        blkcode_re = re.compile(_blkcode_re, re.DOTALL)

        cmds = core.Cmd.syntax.findtokens('cmddef', text)
        inlcodes = inlcode_re.finditer(text)
        blkcodes = blkcode_re.finditer(text)

        tokens = []

        for m in cmds:
            token = core.CmdToken(m.group(1), m.start(0), m.end(0))
            tokens.append(token)
        for m in inlcodes:
            tokentext = core.InlCodeToken.linearize(m.group(1))
            token = core.InlCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)
        for m in blkcodes:
            # find each block and replace first left indent with ''
            tokentext = m.group('code').strip('\n')
            tokentext = core.deltextindent(tokentext)
            token = core.BlkCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)

        tokens.sort(key=lambda tok: tok.start)
        tokens.append(core.EndToken(None))
        return tokens
core.Parser.register(AsciiDocParser)

################################################################################

class TeXParser(core.Parser):
    """TeX parser

    >>> p = TeXParser()
    >>> p._parse('<<cmd>> \\\\verb#text#')
    1
    >>> p.chunkdict.getbypath('cmd')[1].tangle
    'text'

    More complex:
    >>> text = \
    'Some text <<c.fun1>> \\\\verb#fun1-body1# and \\\\verb!fun2-body2! then\\n' \
    '<<c.fun2>> \\\\verb{fun2-body}'
    >>> p = TeXParser()
    >>> p._parse(text)
    3
    >>> p.chunkdict.globpath('c.fun1.*', _onlypath=True)
    ['c.fun1.0', 'c.fun1.1']
    >>> p.chunkdict.globpath('c.fun2', _onlypath=True)
    ['c.fun2']
    >>> p.chunkdict.getbypath('c.fun1.0')[1].orig
    'fun1-body1'
    >>> p.chunkdict.getbypath('c.fun1.0')[1].tangle
    'fun1-body1'
    >>> p.chunkdict.getbypath('c.fun2')[1].tangle
    'fun2-body'
    """

    descr = 'TeX/LaTeX'
    ext = ('.tex', '.latex')
    inlcmds = ('verb', 'verb*')
    blkcmds = ('verbatim', 'verbatim*')

    config_params = core.Parser.config_params + ['inlcmds:strlist', 'blkcmds:strlist']

    def __init__(self, engine=None, parent=None):
        core.Parser.__init__(self, engine, parent)

    def tokens(self, text):
        """Returns tokens

        >>> text = \
        '\\\\documentclass[12pt]{article}\\n' \
        '\\\\usepackage{amsmath}\\n' \
        '\\\\title{\\\\LaTeX}\\n' \
        '\\\\date{}\\n' \
        '\\\\begin{document}\\n' \
        '  \\\\maketitle\\n' \
        '  \\\\LaTeX{} is a document preparation system for the \\\\TeX{}\\n' \
        '\\n' \
        '  Testing of negative value <<isneg>>: \\\\verb#if a < 0#. Signature will\\n' \
        '  be <<fn.abs.decl>>: \\\\verb!int abs(int a)!. And now:\\n' \
        '  function absolute <<fn.abs>>:\\n' \
        '\\n' \
        '  \\\\begin{verbatim}\\n' \
        '    <<=fn.abs.decl>>\\n' \
        '        if (<<=isneg, x:a>>) return -a;\\n' \
        '        else return a;\\n' \
        '    }\\n' \
        '  \\\\end{verbatim}\\n' \
        '\\n' \
        '  % This is a comment; it will not be shown in the final output.\\n' \
        '  % The following shows a little of the typesetting power of LaTeX:\\n' \
        '  \\\\begin{align}\\n' \
        '    m &= \\\\frac{m_0}{\\\\sqrt{1-\\\\frac{v^2}{c^2}}}\\n' \
        '  \\\\end{align}\\n' \
        '\\\\end{document}'
        >>> p = TeXParser()
        >>> toks = p.tokens(text)
        >>> [tok.__class__.__name__ for tok in toks]
        ['CmdToken', 'InlCodeToken', 'CmdToken', 'InlCodeToken', 'CmdToken', 'BlkCodeToken', 'EndToken']
        >>> toks[0].text
        'isneg'
        >>> toks[1].text
        'if a < 0'
        >>> toks[2].text
        'fn.abs.decl'
        >>> toks[3].text == 'int abs(int a)'
        True
        >>> toks[5].text.startswith('<<=fn.abs.decl>>')
        True
        >>> toks[5].text.endswith('}')
        True
        """
        _inlcmds = '|'.join(re.escape(s) for s in TeXParser.inlcmds)
        # text inside inline chunk
        _inltext = r'{(?P<code1>.+?)}|(?P<s>[+#!])(?P<code2>.+?)(?P=s)'
        _blkcmds = '|'.join(re.escape(s) for s in TeXParser.blkcmds)

        _inlcode_re = r'\\(%s)%s'%(_inlcmds, _inltext)
        _blkcode_re = r'\\begin(\[.+?\])?{(%s)}(?P<code>.*?)\\end{(%s)}'%(_blkcmds, _blkcmds)

        inlcode_re = re.compile(_inlcode_re)
        blkcode_re = re.compile(_blkcode_re, re.DOTALL)

        cmds = core.Cmd.syntax.findtokens('cmddef', text)
        inlcodes = inlcode_re.finditer(text)
        blkcodes = blkcode_re.finditer(text)

        tokens = []

        for m in cmds:
            token = core.CmdToken(m.group(1), m.start(0), m.end(0))
            tokens.append(token)
        for m in inlcodes:
            groups = m.groupdict()
            g = 'code1' if groups['code1'] else 'code2'
            tokentext = core.InlCodeToken.linearize(m.group(g))
            token = core.InlCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)
        for m in blkcodes:
            # find each block and replace first left indent with ''
            tokentext = m.group('code').lstrip('\n').rstrip('\n ')
            tokentext = core.deltextindent(tokentext)
            token = core.BlkCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)

        tokens.sort(key=lambda tok: tok.start)
        tokens.append(core.EndToken(None))
        return tokens
core.Parser.register(TeXParser)

################################################################################

class OOSaxHandler(sax.ContentHandler):
    level = None # current level
    codelevel = None # level where code-chunk was found
    codetype = None # 'inline'|'block'
    text = None # list of text collected fragments
    style = None # name of code-chunk style
    styleinh = None # inheritance of style {name:parent-name}

    def __init__(self, style=''):
        self.style = style
        self.level = 0
        self.codelevel = None
        self.codetype = None
        self.text = []
        self.styleinh = {}
        sax.ContentHandler.__init__(self)

    def _style_extends(self, style, parent):
        """Check does style extend parent style

        >>> o = OOSaxHandler('lpcode')
        >>> o.styleinh = {'P1':'P2', 'P2':'P3', 'P3':'lpcode'}
        >>> o._style_extends('P3', 'lpcode')
        True
        >>> o._style_extends('P2', 'lpcode')
        True
        >>> o._style_extends('P1', 'lpcode')
        True
        >>> o._style_extends('P1', 'P2')
        True
        >>> o._style_extends('P2', 'P3')
        True
        >>> o._style_extends('P3', 'P2')
        False
        >>> o._style_extends('P5', 'P2')
        False
        >>> o._style_extends('P5', 'P6')
        False
        >>> o._style_extends('', 'P6')
        False
        >>> o._style_extends(' ', '')
        False
        """
        if not style or not parent:
            return False
        elif style == parent:
            return True
        else:
            return self._style_extends(self.styleinh.get(style, None), parent)

    def _code_element(self, name, attrs):
        stylename = attrs.get('text:style-name', '')
        if stylename and self._style_extends(stylename, self.style):
            if name == 'text:span':
                return 'inline'
            elif name == 'text:p':
                return 'block'
        return None

    @staticmethod
    def _decode_spec_chars(text):
        """replace special chars with it's real symbols"""
        # see _encode_spec_tag() and startElement()
        text = text.replace(u'\u201D', '"') # "
        text = text.replace(u'\u301D', '"') # "
        text = text.replace(u'\u275D', '"') # "
        text = text.replace(u'\u0022', '"') # "
        text = text.replace(u'\u201F', '"') # "
        text = text.replace(u'\u201C', '"') # "
        text = text.replace(u'\u00AB', '"') # "
        text = text.replace(u'\u00BB', '"') # "
        text = text.replace(u'\u2011', '-') # soft hyphen
        text = text.replace(u'\u00AD', '-') # non-breaking hyphen
        text = text.replace(u'\u00A0', ' ') # non-breaking space
        text = text.replace('@tab@', '\t')
        text = text.replace('@space@', ' ')
        text = text.replace('@line_break@', '\n')
        return text

    @staticmethod
    def _encode_spec_tag(tag, attrs):
        """Encode (replace) special chars with it's internal form.
        If not special char, returns None. Diff. from _decode_spec_chars()
        bcz encode tag, not text"""
        if tag == 'text:tab':
            return '@tab@'
        elif tag == 'text:s':
            n = int(attrs.get('text:c', 1))
            return n*'@space@'
        elif tag == 'text:line-break':
            return '@line_break@'
        else:
            return None

    #def endDocument(self):
        #print ''.join(self.text).encode('cp866', errors='ignore')

    def characters(self, content):
        self.text.append(content)

    #<style:style style:name="P1" style:family="paragraph" style:parent-style-name="lpcode">
    def startElement(self, name, attrs):
        elem = self._code_element(name, attrs)
        if name == 'style:style':
            parentstyle = attrs.get('style:parent-style-name', '')
            stylename = attrs.get('style:name')
            if parentstyle and stylename:
                self.styleinh[stylename] = parentstyle
            # styles inheritance
        elif name in ('text:span', 'text:p'):
            if elem and self.codelevel is None:
                self.codelevel = self.level
                self.codetype = elem
                if self.text[-1] == '@end_inline@' and elem == 'inline':
                    # remove empty @start_inline@@end_inline@
                    self.text.pop()
                elif self.text[-1] == '@end_block@' and elem == 'block':
                    # remove empty @start_block@@end_block@
                    self.text.pop()
                else:
                    self.text.append('@start_%s@'%elem)
            self.level += 1
        else:
            spectag = OOSaxHandler._encode_spec_tag(name, attrs)
            if spectag:
                self.text.append(spectag)

    def endElement(self, name):
        if name in ('text:span', 'text:p'):
            self.level -= 1
            if self.codelevel == self.level:
                self.codelevel = None
                if self.codetype == 'block' and self.text and self.text[-1] != '@line_break@':
                    # make to each block ends with \n
                    self.text.append('@line_break@')
                self.text.append('@end_%s@'%self.codetype)
                self.codetype = None


class OOParser(core.Parser):
    """OpenOffice/LibreOffice parser:
    """

    descr = 'OpenOffice/LibreOffice'
    ext = ('.odt',)
    style = 'lpcode'

    config_params = core.Parser.config_params + ['style']

    def __init__(self, engine=None, parent=None):
        core.Parser.__init__(self, engine, parent)

    # FIXME not sure that works right
    @classmethod
    def findlines(class_, text):
        """Split text to lines coordinates
        """
        #return Parser.findlines(text, delim=('@line_break@', '\n'))
        return None # disable error location

    def readfile(self, file):
        """Return text of document"""
        with zipfile.ZipFile(file) as zip:
            #return zip.read('content.xml').decode('utf8')
            return core.bytestostr23(zip.read('content.xml'))

    def tokens(self, text):
        oosaxhandler = OOSaxHandler(style=self.style)
        # next conversion seems bug in python (why need bytes, not str?!)
        if type(text) is str:
            parsetext = core.strtobytes23(text)
        else:
            parsetext = text
        sax.parseString(parsetext, oosaxhandler)
        text = ''.join(oosaxhandler.text)

        _inlcode_re = r'@start_inline@(.*?)@end_inline@'
        _blkcode_re = r'@start_block@(.*?)@end_block@'

        inlcode_re = re.compile(_inlcode_re, re.MULTILINE)
        blkcode_re = re.compile(_blkcode_re, re.MULTILINE)

        cmds = core.Cmd.syntax.findtokens('cmddef', text)
        inlcodes = inlcode_re.finditer(text)
        blkcodes = blkcode_re.finditer(text)

        tokens = []

        for m in cmds:
            token = core.CmdToken(OOSaxHandler._decode_spec_chars(m.group(1)), m.start(0), m.end(0))
            tokens.append(token)
        for m in inlcodes:
            # XXX break line in OO is coded with paragraph styling and this linearizing
            # does not help
            tokentext = OOSaxHandler._decode_spec_chars(m.group(1))
            tokentext = core.InlCodeToken.linearize(tokentext)
            token = core.InlCodeToken(tokentext, m.start(0), m.end(0))
            tokens.append(token)
        for m in blkcodes:
            token = core.BlkCodeToken(OOSaxHandler._decode_spec_chars(m.group(1)), m.start(0), m.end(0))
            tokens.append(token)

        tokens.sort(key=lambda tok: tok.start)
        tokens.append(core.EndToken(None))
        #print [t.text for t in tokens]
        return tokens
core.Parser.register(OOParser)

################################################################################

class XHTMLSaxHandler(sax.ContentHandler):
    level = None # current level
    codelevel = None # level where code-chunk was found
    codetype = None # 'inline'|'block'
    text = None # list of text collected fragments
    styles = None # name of code-chunk style
    tags = None # tags of code-chunks
    tag_to_close = None # tag waited to be close
    tagstack = None # stack of tags

    def __init__(self, styles=[], tags=[]):
        self.styles = styles
        self.tags = tags
        self.tag_to_close = None
        self.tagstack = []
        self.level = 0
        self.codelevel = None
        self.codetype = None
        self.text = []
        sax.ContentHandler.__init__(self)

    def _code_element(self, name, attrs):
        """If tag for code chunk (with name) and attrs matched, returns it's
        type - 'block', otherwise - None

        >>> h = XHTMLSaxHandler(styles=[], tags=['pre', 'code'])
        >>> h._code_element('pre', {})
        'block'
        >>> h._code_element('code', {})
        'block'
        >>> h._code_element('code', {'class':'xxx yyy'})
        'block'
        >>> h = XHTMLSaxHandler(styles=['lpcode'], tags=['pre'])
        >>> h._code_element('pre', {'class': 'lpcode other'})
        'block'
        >>> h._code_element('pre', {'class': 'other lpcode'})
        'block'
        >>> h._code_element('pre', {})
        >>> h._code_element('code', {'class': 'lpcode'})
        >>> h = XHTMLSaxHandler(styles=['lpcode', 'other'], tags=[])
        >>> h._code_element('code', {'class': 'lpcode'})
        'block'
        >>> h._code_element('pre', {'class': 'other'})
        'block'
        >>> h._code_element('pre', {'class': 'xxx other yyy'})
        'block'
        """
        styles = attrs.get('class', '').split()
        if self.tags:
            if name not in self.tags: return None
        if self.styles:
            if all(style not in self.styles for style in styles):
                return None
        return 'block' # all is block

    @staticmethod
    def _decode_spec_chars(text):
        """replace special chars with it's real symbols"""
        text = text.replace(u'\u201D', '"') # "
        text = text.replace(u'\u301D', '"') # "
        text = text.replace(u'\u275D', '"') # "
        text = text.replace(u'\u0022', '"') # "
        text = text.replace(u'\u201F', '"') # "
        text = text.replace(u'\u201C', '"') # "
        text = text.replace(u'\u00AB', '"') # "
        text = text.replace(u'\u00BB', '"') # "
        text = text.replace(u'\u2011', '-') # soft hyphen
        text = text.replace(u'\u00AD', '-') # non-breaking hyphen
        text = text.replace(u'\u00A0', ' ') # non-breaking space
        text = text.replace('@line_break@', '\n')
        return text

    def characters(self, content):
        if 'head' not in self.tagstack:
            # append only out of 'HEAD'
            self.text.append(content)

    #<tag class=..>
    def startElement(self, name, attrs):
        self.tagstack.append(name.lower())
        elem = self._code_element(name, attrs)
        if elem and self.codelevel is None:
            self.codelevel = self.level
            self.codetype = elem
            self.tag_to_close = name
            if self.text[-1] == '@end_inline@' and elem == 'inline':
                # remove empty @start_inline@@end_inline@
                self.text.pop()
            elif self.text[-1] == '@end_block@' and elem == 'block':
                # remove empty @start_block@@end_block@
                self.text.pop()
            else:
                self.text.append('@start_%s@'%elem)
        self.level += 1

    def endElement(self, name):
        self.tagstack.pop()
        self.level -= 1
        if name == self.tag_to_close:
            if self.codelevel == self.level:
                self.codelevel = None
                #if self.codetype == 'block' and self.text and self.text[-1] != '@line_break@':
                    # make to each block ends with \n
                    #self.text.append('@line_break@')
                self.text.append('@end_%s@'%self.codetype)
                self.tag_to_close = None
                self.codetype = None


class XHTMLSaxErrorHandler(sax.ErrorHandler):
    def __init__(self, parser, ignore=[]):
        self.parser = parser
        self.ignore = ignore

    def error(self, exception):
        if not 'error' in self.ignore:
            raise exception

    def fatalError(self, exception):
        if not 'fatal' in self.ignore:
            raise exception

    def warning(self, exception):
        if not 'warning' in self.ignore:
            core.prn(str(exception), engine=self.parser.engine, file='stderr')


class XHTMLParser(core.Parser):
    """HTML/XML parser:
    """

    descr = 'HTML/XML'
    ext = ('.html', '.shtml', '.htm')
    styles = ('lpcode',)
    tags = ('pre', 'code')
    ignore = () # may be 'error', 'fatal', 'warning' (see XHTMLSaxErrorHandler)

    config_params = core.Parser.config_params + ['styles:strlist', 'tags:strlist', 'ignore:strlist']

    def __init__(self, engine=None, parent=None):
        core.Parser.__init__(self, engine, parent)
        if not (self.styles or self.tags):
            raise ValueError('XHTMLParser needs styles or tags')

    @classmethod
    def findlines(class_, text):
        """Split text to lines coordinates
        """
        return None # disable error location

    def tokens(self, text):
        xhtmlsaxhandler = XHTMLSaxHandler(styles=self.styles, tags=self.tags)
        xhtmlsaxerrhandler = XHTMLSaxErrorHandler(self, self.ignore)
        # next conversion seems bug in python (why need bytes, not str?!)
        if type(text) is str:
            parsetext = core.strtobytes23(text)
        else:
            parsetext = text
        sax.parseString(parsetext, xhtmlsaxhandler, xhtmlsaxerrhandler)
        text = ''.join(xhtmlsaxhandler.text)

        #_inlcode_re = r'@start_inline@(.*?)@end_inline@'
        _blkcode_re = r'@start_block@(.*?)@end_block@'

        #inlcode_re = re.compile(_inlcode_re, re.MULTILINE)
        blkcode_re = re.compile(_blkcode_re, re.DOTALL|re.MULTILINE)

        cmds = core.Cmd.syntax.findtokens('cmddef', text)
        #inlcodes = inlcode_re.finditer(text)
        blkcodes = blkcode_re.finditer(text)

        tokens = []

        for m in cmds:
            token = core.CmdToken(XHTMLSaxHandler._decode_spec_chars(m.group(1)), m.start(0), m.end(0))
            tokens.append(token)
        #for m in inlcodes:
        #    # XXX break line in HTML is coded with paragraph styling and this linearizing
        #    # does not help
        #    tokentext = XHTMLSaxHandler._decode_spec_chars(m.group(1))
        #    tokentext = core.InlCodeToken.linearize(tokentext)
        #    token = core.InlCodeToken(tokentext, m.start(0), m.end(0))
        #    tokens.append(token)
        for m in blkcodes:
            tokentext = m.group(1).lstrip('\n').rstrip('\n ')
            tokentext = core.deltextindent(tokentext)
            token = core.BlkCodeToken(XHTMLSaxHandler._decode_spec_chars(tokentext), m.start(0), m.end(0))
            tokens.append(token)

        tokens.sort(key=lambda tok: tok.start)
        tokens.append(core.EndToken(None))
        return tokens
core.Parser.register(XHTMLParser)

################################################################################
