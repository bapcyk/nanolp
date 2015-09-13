# Utils for NanoLP
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

import os
import re
import json
import shutil
import itertools
import collections
import xml.sax.saxutils as saxutils
import nanolp.core as core

__HOMEURL__ = 'http://code.google.com/p/nano-lp'
__BLOGURL__ = 'http://balkansoft.blogspot.com'
__BLOGNAME__ = 'BalkanSoft.BlogSpot.Com'

def snumerate(obj, collection, fmt=None):
    """numerate object with numeric suffix like 'obj(2)'

    >>> c = []
    >>> snumerate(1, c)
    '1'
    >>> snumerate(1, c)
    '1(2)'
    >>> snumerate(1, c)
    '1(3)'
    >>> snumerate(1, c, '%s -- %d')
    '1 -- 4'
    >>> snumerate(1, c, lambda o,n:'%s..%d'%(o,n))
    '1..5'
    """
    if not fmt:
        _fmt = lambda o,n: '%s(%d)'%(o,n)
    elif isinstance(fmt, core.StringTypes23):
        _fmt = lambda o,n: fmt%(o,n)
    else:
        _fmt = fmt
    obj = str(obj)
    nrepeats = collection.count(obj)
    collection.append(obj)
    if nrepeats:
        return _fmt(obj, nrepeats+1)
    else:
        return '%s'%obj

class RefsFile:
    """Generates references HTML file"""

    CSSFILENAME = 'nanolp.css'

    parser = None
    inputattrs = ''

    def __init__(self, parser, title=''):
        self.parser = parser
        self.inputattrs = self.__uriattrs(core.Uri(self.parser.infile))
        self.title = title

    def __url(self, obj):
        """Return URL to obj; obj is Uri/Cmd. If Uri is FS-path, try to return
        relative URL instead of full 'file://...'
        """
        if isinstance(obj, core.Cmd):
            return obj.jpath()
            #return base64.b64encode(obj.jpath())
            #return str(hash(obj.jpath())).replace('-', '_')
        elif isinstance(obj, core.Uri):
            if obj.islocal():
                objdir = os.path.dirname(obj.fspath)
                relpath = os.path.relpath(objdir, self.parser.outdir)
                if '.' == relpath:
                    # if in the same output directory, URL is file name
                    return obj.name
                elif '..' not in relpath:
                    # if is internal in parser.outdir, URL is relative
                    return os.path.join(relpath, obj.name)
                else:
                    # else is out of parser.outdir, so URL will be full qualified
                    return obj.url # it's "file://fspath"
            else:
                return obj.url
        else:
            raise RuntimeError("Can not generate URL for '%s'"%str(obj))

    def __uriattrs(self, uri):
        """Uri as attributes for <a> tag: url, title, orig name, short-name (moniker)"""
        return dict(url=self.__url(uri),
                name=uri.name,
                title=uri.fspath or uri.url,
                moniker=uri.getmoniker())

    def _header(self):
        return ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">',
        '<html xmlns="http://www.w3.org/1999/xhtml">',
        '<head>',
        '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>',
        '<link rel="stylesheet" href="%s" type="text/css"/>' % self.CSSFILENAME,
        '<title>%s: references</title>' % self.inputattrs['name'],
        '</head>',
        '<body>')

    def _footer(self):
        yield '<div id="about">'
        yield '<a href="%s">%s</a> - ' % (__HOMEURL__, core.__ABOUT__)
        yield '<a href="%s">%s</a>'%(__BLOGURL__, __BLOGNAME__)
        yield '</div></body></html>'

    def _output_info(self):
        """HTML tags for info about parser and it's results"""
        yield '<table class="outputinfo">'
        # Outputs - all FileCmd's
        cmds = self.parser.chunkdict.get_uniform_commands('FileCmd')
        yield '<tr>'
        yield '<td class="param">Outputs:</td>'
        yield '<td>'
        for cmd in cmds:
            if not cmd.outfile:
                # if flushing of files is disable, FileCmd.onpost() will not be call, so
                # cmd.outfile will be unset
                yield '<i title="Flush of files is disabled">%s</i>'%(cmd.body[0] or 'no output')
            else:
                uriattrs = self.__uriattrs(core.Uri(cmd.outfile))
                yield '<a title="%s" href="%s">%s</a>&nbsp;&nbsp;' % \
                        (uriattrs['title'], uriattrs['url'], uriattrs['name'])
        yield '</td>'
        yield '</tr>'
        # Includes - all UseCmd's
        cmds = self.parser.chunkdict.get_uniform_commands('UseCmd')
        yield '<tr>'
        yield '<td class="param">Includes:</td>'
        yield '<td>'
        for cmd in cmds:
            uriattrs = self.__uriattrs(core.Uri(cmd.infile))
            yield '<a title="%s" href="%s">%s</a>&nbsp;&nbsp;' % \
                    (uriattrs['title'], uriattrs['url'], uriattrs['name'])
        yield '</td>'
        yield '</tr>'
        # Config file
        if self.parser.engine:
            yield '<tr>'
            yield '<td class="param">Cfg. file:</td>'
            yield '<td>'
            cfgfile = self.parser.engine.cfgfile.filename
            uriattrs = self.__uriattrs(core.Uri(cfgfile))
            yield '<a href="%s" title="%s">%s</a>' % \
                    (uriattrs['url'], uriattrs['title'], uriattrs['name'])
            yield '</td>'
            yield '</tr>'
        # Index of commands
        cmds = self.parser.chunkdict.keys()
        yield '<tr>'
        yield '<td class="param">Index:</td>'
        yield '<td>'
        url_collection = []; jpath_collection = []
        for cmd in sorted(cmds, key=lambda c:c.jpath()):
            url = snumerate(self.__url(cmd), url_collection)
            jpath = snumerate(cmd.jpath(), jpath_collection)
            yield '<a href="#%s">%s</a>&nbsp;&nbsp;' % (url, jpath)
        yield '</td>'
        yield '</tr>'
        # Variables
        # XXX sort only for tests
        pre = collections.OrderedDict()
        for k in sorted(self.parser.vars.keys()):
            d = self.parser.vars[k]
            pre[k] = collections.OrderedDict(d)
        pre = json.dumps(pre)
        yield '<tr>'
        yield '<td class="param">Variables:</td>'
        yield '<td>'
        if pre:
            yield '<pre class="code">'
            yield pre
            yield '</pre>'
        yield '</td>'
        yield '</tr>'
        yield '</table>'

    def __cmdref(self, cmd):
        """Returns <a> HTML tag (for cmd or list of commands-dependencies) OR
        tags for popup box"""
        jpath = cmd.jpath()
        for ch in jpath:
            if ch in ('?', '*', '['):
                break # glob path
        else:
            # not glob path
            return '<a href="#%s">%s</a>' % (self.__url(cmd), cmd.text)
        # glob path
        popup = ['<span class="popup">%s'%cmd.text, '<div><span id="caption">Matched:</span>']
        cmds = self.parser.chunkdict.globpath(jpath)
        for cmd in cmds:
            popup.append(self.__cmdref(cmd))
        popup.append('</div></span>')
        return ''.join(popup)

    def _body(self):
        yield '<div id="ctrlbar">'
        yield '<h1><span class="dlarrow"><a href="%s" title="%s">&dArr;</a></span>%s: references</h1>' % \
                (self.inputattrs['url'], self.inputattrs['title'], self.inputattrs['moniker'])
        for y in self._output_info(): yield y
        yield '</div>'

        url_collection = []; jpath_collection = []
        for cmd, chunk in self.parser.chunkdict.chunks.items():
            url = snumerate(self.__url(cmd), url_collection)
            jpath = snumerate(cmd.jpath(), jpath_collection)
            yield '<h2><a name="%s">%s</a></h2>'%(url, jpath)

            yield '<table class="chunkinfo">'

            yield '<tr>'
            yield '<td class="param">pos-args:</td>'
            yield '<td>'
            last = len(cmd.body)-1; i = 0
            for posarg in cmd.body:
                yield saxutils.escape(posarg)
                if i != last: yield ', '
                i += 1
            yield '</td>'
            yield '</tr>'

            yield '<tr>'
            yield '<td class="param">kw-args:</td>'
            yield '<td>'
            last = len(cmd.args)-1; i = 0
            for n, v in cmd.args:
                yield '%s : %s' % (saxutils.escape(n), saxutils.escape(v))
                if i != last: yield ', '
                i += 1
            yield '</td>'
            yield '</tr>'

            yield '<tr>'
            yield '<td class="param">chunk:</td>'
            if chunk.orig:
                chunkorig = chunk.orig
                # next trick is replacing dep text with <A HREF> (or popup)
                # and escaping it's text without to escape <A HREF>/popup
                deprefs = []
                for dep in chunk.deps:
                    chunkorig = chunkorig.replace(dep.text, '__DEP:%d:'%len(deprefs))
                    # add one dep, but its jpath may be glob (matched several cmd's),
                    # so __cmdref() detects real number of dep's
                    deprefs.append(dep)
                chunkorig = saxutils.escape(chunkorig)
                chunkorig = re.sub(r'__DEP:(.+?):',
                        lambda m: self.__cmdref(deprefs[int(m.group(1))]),
                        chunkorig)
                yield '<td><pre class="code">%s</pre></td>' % chunkorig
            else:
                yield '<td>&nbsp;</td>'
            yield '</tr>'

            yield '</table>'
            yield '<hr width="100%" />'

    def save(self):
        cssfname = os.path.join(self.parser.outdir, self.CSSFILENAME)
        if not os.path.exists(cssfname):
            # if CSS file doesnt exists, create
            core.prn("writing CSS-styles file '%s'..."%cssfname, engine=self.parser.engine, file='stdout')
            shutil.copyfile(core.extrapath(self.CSSFILENAME), cssfname)
            #core.fwrite23(cssfname, self._css)

        #if not self.parser.infile:
            # define output file name
            #fname = 'nanolp-refs.html'
        #else:
            #fname = os.path.split(self.parser.infile)[1] + '-refs.html'
        fname = self.inputattrs['name'] + '-refs.html'
        fname = os.path.join(self.parser.outdir, fname)

        lines = itertools.chain(self._header(), self._body(), self._footer())
        text = '\n'.join(lines)
        core.prn("writing references file '%s'..."%fname, engine=self.parser.engine, file='stdout')
        core.fwrite23(fname, text)

################################################################################

class Publisher:
    """Prepare HTML file for publishing
    """
    CSSFILENAME = 'nanolp-pub.css'
    JSFILENAME = 'nanolp-pub.js'

    _script0 = "var LP_CFG = {{'SURR':{SURR}, 'CMDS':{CMDS}}};"

    parser = None
    baseurl = ''

    def __init__(self, parser, baseurl=''):
        self.parser = parser
        if baseurl and not re.match(r'\w+://', baseurl, re.I):
            baseurl = 'http://' + baseurl
        self.baseurl = baseurl

    def __url(self, path):
        """Returns URL for files (css, js) and infile's of defined chunks
        """
        uri = core.Uri(path)
        if uri.islocal():
            dir = os.path.dirname(uri.fspath)
            relpath = os.path.relpath(dir, self.parser.outdir)
            if '.' == relpath:
                # if in the same output directory, URL is file name
                relpath = uri.name
            elif '..' not in relpath:
                # if is internal in parser.outdir, URL is relative
                relpath = os.path.join(relpath, uri.name)
            else:
                # else is out of parser.outdir, so URL will be full qualified
                raise RuntimeError("Can not generate URL for '%s'"%str(path))
            # TODO may be need some escaping/quoting?
            return relpath if not self.baseurl else '/'.join((self.baseurl, relpath))
        else:
            return uri.url

    def publish(self, filename):
        # modify input HTML...
        tokstream = core.HTMLTokensStream()
        tokstream.feed(core.fread23(filename))
        headpos = 0
        for itok, tok in enumerate(tokstream.tokens):
            if tok.match(tag='script', kind=core.HTMLToken.OPEN,
                    attrs={'src':'/.*?%s.*?/'%re.escape(self.JSFILENAME)}):
                raise RuntimeError('This document is already modified')
            if tok.match(tag='head', kind=core.HTMLToken.CLOSE):
                headpos = itok
                break

        # Script 0
        cmds = collections.OrderedDict()
        for cmd in self.parser.chunkdict.keys():
            infile = cmd.srcinfo.infile
            if infile:
                infile = "" if infile == self.parser.infile else self.__url(infile)
            cmds[cmd.jpath()] = infile
        fmtargs = {
                'SURR': self.parser.surr,
                'CMDS': cmds,
        }
        for k,v in fmtargs.items():
            fmtargs[k] = json.dumps(v).replace('"', "'") # ' instead of "
        text = self._script0.format(**fmtargs)
        script0 = [
                core.HTMLToken(tag='script', kind=core.HTMLToken.OPEN,
                    attrs={'type': 'text/javascript'}, data=text),
                core.HTMLToken(tag='script', kind=core.HTMLToken.CLOSE)]

        # Script 1
        script1 = [
                core.HTMLToken(tag='script', kind=core.HTMLToken.OPEN,
                    attrs='src=%s|type=text/javascript'%self.__url(self.JSFILENAME)),
                core.HTMLToken(tag='script', kind=core.HTMLToken.CLOSE)]

        # Stylesheet
        css = [
                core.HTMLToken(tag='link', kind=core.HTMLToken.SINGLE,
                    attrs='href=%s|rel=stylesheet|type=text/css'%self.__url(self.CSSFILENAME))]

        # Head inserts
        tokstream.tokens[headpos:headpos] = css + script0 + script1

        # Save to file
        xml = ''.join(tokstream.serialize())
        core.prn("modifying '%s' for publish..."%filename, engine=self.parser.engine, file='stdout')
        core.fwrite23(filename, xml)

        # Flush additional files
        indir = os.path.dirname(filename)
        cssfname = os.path.join(indir, self.CSSFILENAME)
        jsfname = os.path.join(indir, self.JSFILENAME)
        if not os.path.exists(cssfname):
            core.prn("writing CSS-styles file '%s'..."%cssfname, engine=self.parser.engine, file='stdout')
            shutil.copyfile(core.extrapath(self.CSSFILENAME), cssfname)
            #core.fwrite23(cssfname, self._css)
        if not os.path.exists(jsfname):
            core.prn("writing JS file '%s'..."%jsfname, engine=self.parser.engine, file='stdout')
            shutil.copyfile(core.extrapath(self.JSFILENAME), jsfname)
            #core.fwrite23(jsfname, self._script1)

################################################################################

