#!/usr/bin/env python

# Main module (to run from command line)
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

import getopt
import sys
import os
from nanolp import lp
from nanolp.core import __ABOUT__

################################################################################

class AppError(Exception): pass

class App:
    input_file = None # input file name
    cfgfile = '' # path to config. file
    urlcfgfile = '' # path to url config. file
    tb = False # show traceback on exceptions
    refs = False # flush references file
    quiet = False # no messages to console
    fmt = None # forsed format of input file
    outdir = None # output directory
    publish = None # publish URL (if publish option is used)

    def print_usage(self):
        def parser_info(cls):
            ext = '%s' % ', '.join(cls.ext)
            return '   %s - %s: %s'%(cls.__name__, cls.descr or 'Unknown', ext)

        def cmd_info(cls):
            return '   %s - %s'%(cls.__name__, cls.descr or 'Unknown')

        def fetcher_info(cls):
            return '   %s - %s'%(cls.__name__, cls.descr or 'Unknown')

        formats = [parser_info(p) for p in lp.Parser.parsers]
        formats = '\n'.join(formats)
        commands = [cmd_info(c) for c in lp.Cmd.commands]
        commands = '\n'.join(commands)
        fetchers = [fetcher_info(c) for c in lp.Vfile.vfiles]
        fetchers = '\n'.join(fetchers)

        if self.cfgfile or self.urlcfgfile:
            cfginfo = "Setup from: '%s', '%s'" % (self.cfgfile, self.urlcfgfile)
        else:
            cfginfo = ''

        USAGE = '''\
%s
Syntax: -i FILE [-f FMT] [-c CFG] [-u URLCFG] [-o DIR] [-x] [-r] [-p URL] [-q]
[-h]
   -i FILE      Input file or URL
   -f FMT       Force format (extension)
   -c CFG       Path to configuration file
   -u URLCFG    Path to URL configuration file
   -o DIR       Output directory
   -x           Detailed stack-trace on errors
   -r           Flush references file
   -p URL       Prepare HTML for WEB publishing (with base URL or '.' to skip)
   -q           Quiet
   -h           This help
Supported formats:
%s
Special commands:
%s
Supported schemes:
%s
%s'''%(__ABOUT__, formats, commands, fetchers, cfginfo)
        lp.prn(USAGE, file='stdout', quiet=self.quiet)

    def parse_cmdline(self):
        """Returns True, if app may continue execution, False otherwise
        (help printing is only need)
        """
        try:
            opts, args = getopt.getopt(sys.argv[1:], 'rxqhi:f:c:u:o:p:', [])
        except getopt.GetoptError as x:
            sys.stderr.write('Syntax error! See help (-h)\n')
            sys.exit(1)

        self.input_file = None
        _UsageAndExit = False
        for o, v in opts:
            if o == '-h':
                _UsageAndExit = True
            elif o == '-i':
                self.input_file = v
            elif o == '-f':
                self.fmt = v
            elif o == '-c':
                self.cfgfile = v
            elif o == '-u':
                self.urlcfgfile = v
            elif o == '-o':
                self.outdir = v
            elif o == '-x':
                self.tb = True
            elif o == '-r':
                self.refs = True
            elif o == '-p':
                self.publish = '' if v == '.' else v
            elif o == '-q':
                self.quiet = True

        if _UsageAndExit:
            return False

        if not self.input_file:
            lp.prn('Input file is mandatory. See help (-h)', file='stderr', quiet=self.quiet)
            sys.exit(1)
        return True

    # XXX first call parse_cmdline() to determine input dir (as possible place
    # of cfg. file)
    def ensurecf(self, fname='lprc'):
        """Return path to some cfg file with name fname or raise exception, if not found.
        Priority of search:
            - folder of input file
            - current working directory
            - script directory
        """
        dirs = [os.getcwd(), os.path.dirname(os.path.realpath(__file__))]
        if self.input_file:
            # input dir has higher priority for search of cfgfile
            absp = os.path.abspath(self.input_file)
            dirs.insert(0, os.path.dirname(absp))
        for indir in dirs:
            cfgfile = os.path.join(indir, fname)
            if os.path.exists(cfgfile):
                return cfgfile
        raise AppError("Can not found '%s' configuration file"%fname)

    def main(self):
        onlyhelp = not self.parse_cmdline()

        def _do():
            """real action"""
            if not self.cfgfile:
                self.cfgfile = self.ensurecf('lprc')
            if not self.urlcfgfile:
                self.urlcfgfile = self.ensurecf('lpurlrc')

            if onlyhelp:
                self.print_usage()
                sys.exit(0)

            if self.publish is not None:
                # if need to publish...
                engine = lp.Lp(cfgfile=self.cfgfile, urlcfgfile=self.urlcfgfile, quiet=self.quiet, outdir=self.outdir)
                parser = lp.Parser.create_parser(engine, self.input_file, fmt=self.fmt)
                parser.parsefile(self.input_file, flush=False)
                pub = lp.Publisher(parser, baseurl=self.publish)
                pub.publish(self.input_file)
            else:
                engine = lp.Lp(cfgfile=self.cfgfile, urlcfgfile=self.urlcfgfile, quiet=self.quiet, outdir=self.outdir)
                parser = lp.Parser.create_parser(engine, self.input_file, fmt=self.fmt)
                parser.parsefile(self.input_file)

            if self.refs:
                # if need to flush references...
                fn = os.path.split(self.input_file)[1]
                fn = fn.upper()
                refsfile = lp.RefsFile(parser, "%s: references"%fn)
                refsfile.save()

        if self.tb:
            _do()
        else:
            try:
                _do()
            except Exception as x:
                lp.prn("ERROR '%s': %s"%(x.__class__.__name__,str(x)), file='stderr', quiet=self.quiet)
                sys.exit(1)

################################################################################

if __name__ == "__main__":
    app = App()
    app.main()
