# Special Commands
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

import os
import re
import nanolp.core as core

class UseCmd(core.Cmd):
    """Processor of <<use...>> command"""
    descr = 'Import one LP file to another'
    gpath = "use"

    infile = '' # path to included file or file-obj (i.e., url-object)

    def onpost(self, parser=None, flush=None):
        chunk = parser.chunkdict.getbykey(self)
        infile = ''.join(self.body)
        mnt = self.getarg('mnt', '')
        fmt = self.getarg('fmt', '')
        self.infile = parser.ensureinput(infile)
        if not self.infile:
            raise core.ParserError("'use' can not ensure '%s' input file"%infile)
        core.prn("using '%s' mounted to '%s'..."%(self.infile, mnt), engine=parser.engine, file='stdout')
        inclparser = core.Parser.create_parser(parser.engine, self.infile, fmt=fmt, parent=parser)
        inclparser.parsefile(self.infile, flush=False)
        parser.importparser(inclparser, mnt)
        return core.Cmd.onpost(self, parser=parser, flush=flush)
core.Cmd.register(UseCmd)

################################################################################

class FileCmd(core.Cmd):
    """Processor of <<file...>> command"""
    descr = 'Save it\'s content to file'
    gpath = "file.*"

    outfile = '' # path to output file

    def onpost(self, parser=None, flush=None):
        if flush:
            jpath = self.jpath()
            chunk = parser.chunkdict.getbykey(self)
            if not parser.expand(jpath):
                raise core.ParserError("'%s' can not be expanded"%jpath)
            # body of out is output file name
            self.outfile = ''.join(self.body)
            self.outfile = os.path.join(parser.outdir, self.outfile)
            self.outfile = os.path.abspath(self.outfile)
            # if self.outfile has relative path, real outdir can be different then
            # in parser. If not exists, create it
            outdir = os.path.dirname(self.outfile)
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            core.prn("writing to '%s'..."%self.outfile, engine=parser.engine, file='stdout')
            core.fwrite23(self.outfile, chunk.tangle)
        return core.Cmd.onpost(self, parser=parser, flush=flush)
core.Cmd.register(FileCmd)

################################################################################

class VarsCmd(core.Cmd):
    """Processor of <<vars...>> command"""
    descr = 'Create variables dictionary'
    gpath = "vars"

    def ondefine(self, parser=None, chunktext=None):
        """Add dictionary of vars, body[0] of Cmd will be name of dict
        otherwise anonym. dict is used
        """
        parser.updatevars(self.body[0] if self.body else '', dict(self.args))
        return core.Cmd.ondefine(self, parser=parser, chunktext=None)
core.Cmd.register(VarsCmd)

################################################################################

class OnCmd(core.Cmd):
    """Processor of <<on.CLASS...>> command"""
    descr = 'Set event handler'
    gpath = 'on.*'

    def __ondefine__(self, parser=None, chunktext=None):
        """__ - means out of event-handling (hidden for handlers)"""
        handlers = []
        classname = self.path[1]
        class_ = getattr(core, classname)
        gpath = self.getarg('gpath')
        if len(self.path) > 2:
            # 'on.CLASS.EVENT, gpath:xxx, do:xxx'
            event = self.path[2]
            functext = self.getarg('do')
            func = core.LineExp().parse(functext)
            func.setcontext(resolver=parser,
                    stdargs=core.EventHandler.getargspec(class_, event).args)
            params = dict(classname=classname, gpath=gpath, event=event)
            handlers.append(core.EventHandler(func, **params))
        else:
            # 'on.CLASS, gpath:xxx, do.EVENT1:xxx, do.EVENT2:xxx...'
            for argname, argvalue in self.args:
                if argname.startswith('do.'):
                    # some handler
                    event = argname[3:] # 3==len('do.')
                    functext = argvalue
                    func = core.LineExp().parse(functext)
                    func.setcontext(resolver=parser,
                            stdargs=core.EventHandler.getargspec(class_, event).args)
                    params = dict(classname=classname, gpath=gpath, event=event)
                    handlers.append(core.EventHandler(func, **params))
        parser.updatehandlers(handlers)
        return core.Cmd.ondefine(self, parser=parser, chunktext=None)
core.Cmd.register(OnCmd)

################################################################################
