# Itself testing facilities
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

from nanolp import core
from nanolp import commands
from nanolp import parsers
from nanolp import utils
from nanolp import lp
from nanolp import _instlog
import unittest as ut
import doctest as dt
import os
import sys
import glob
import time
import shutil
import getopt
import random
import subprocess
import re

## modules to be tested with docstrings
DOCTESTMODULES = (core, parsers, utils)

class TestCfg:
    """Interface to config params"""
    _SUFFIX = '_PARAM'
    def __init__(self, configmodule):
        self._config = configmodule
    def get(self, param):
        """Getter of param. value"""
        param = param.upper() + TestCfg._SUFFIX
        return getattr(self._config, param)
    def __getattr__(self, param):
        """Access to param. value as attribute (without '_PARAM' suffix!)"""
        return self.get(param)
    def keys(self):
        """Iterator over config. param. names"""
        for v in self._config.__dict__.keys():
            if v.endswith('_PARAM'): yield v[:-len(TestCfg._SUFFIX)]
# config params access
from nanolp.test import config
_testcfg = TestCfg(config)

################################################################################

def substitute_infile(indir, inbuf):
    """Substitutes all vars in .in file
        $__ABOUT__
        $__VERSION__
        ${REPLACE-DIRECTIVE ARG|...}
    REPLACE-DIRECTIVE is the suffix one of nested replXXX() functions.
    Piping means: if first, call with this arg, all other calls with result
    from previous or own arg (if no prev. result)
    """
    def replABSPATH(arg):
        """Replaces PATH with real abs path in platform-independent way"""
        return os.path.abspath(os.path.join(indir, arg))
    def replNORMPATH(arg):
        """Replaces PATH with normalized path in platform-independent way
        (not absolute!)"""
        return os.path.normpath(arg)
    def replPYINFO(arg):
        """Replace it with info about python"""
        if arg == 'exec': return sys.executable
        elif arg == 'ver': return sys.version
        else: raise ValueError("Wrong argument '%s' for PYINFO"%arg)
    def replCMDESC(arg):
        """Escape text as for Cmd input"""
        re_ = '(%s)'%('|'.join(re.escape(ch) for ch in core.CMDQUOTE))
        cre = re.compile(re_)
        arg = cre.sub(r'\\\1', arg)
        return arg

    replfuncs = dict((k,v) for k,v in locals().items() if k.startswith('repl'))

    def _replALL(m, replfuncs=replfuncs):
        """Make chained replacing"""
        text = m.group(1)
        res = ''
        for fragment in text.split('|'):
            fragment = fragment.strip()
            cmdarg = fragment.split(' ', 1)
            cmd = cmdarg[0]; arg = cmdarg[1] if len(cmdarg)>1 else ''
            replfunc = replfuncs.get('repl%s'%cmd, None) # func. name must be repl<CMD>
            if not replfunc: return m.group(0) # not my directive, keep original text
            res = replfunc(res or arg)
        return res

    # Substitutes all what needed
    COREVARSNAMES = ('__ABOUT__', '__VERSION__')
    TESTVARSNAMES = list(_testcfg.keys())
    # substitute vars first $...
    for v in COREVARSNAMES:
        inbuf = inbuf.replace('$%s'%v, '%s'%getattr(core, v))
    for v in TESTVARSNAMES:
        inbuf = inbuf.replace('$%s'%v, '%s'%_testcfg.get(v))
    # substitute expressions ${...}
    inbuf = re.sub(r'\$\{(.+?)\}', _replALL, inbuf)
    return inbuf

def process_infile(indir, infile):
    """Process infile (.in) - substitutes and create reflection file
    (with the same name but without '.in' extension)"""
    f = change_ext(infile, '')
    shutil.copyfile(infile, f)
    buf = core.fread23(f)
    buf = substitute_infile(indir, buf)
    core.fwrite23(f, buf)

def msgfmt(msg, *args, **opts):
    caption = opts.get('caption', 'REASON')
    msg = msg % args
    return '\n>>> %s: %s\n'%(caption, msg)

def rmoutfiles(indir):
    """Remove all out files ('xxx.ext' from 'xxx.ext.master') in directory indir"""
    def _rmreflectionof(ext):
        """Remove reflection of some extension; reflection
        is the same file but without extension"""
        for master in globfiles(indir, '*.%s'%ext, True):
            out = master.replace('__', os.sep)
            out = change_ext(out, '')
            if os.path.exists(out):
                os.remove(out)
    _rmreflectionof('master')
    _rmreflectionof('in')

def readfile(filename):
    """Return buffer from *.master file"""
    return core.fix_crlf(core.fread23(filename)).rstrip('\r\n')

def globfiles(indir, patt, rec=False):
    """Return list of globbing files from directory indir with pattern.
    """
    files = []
    for root, dirnames, filenames in os.walk(indir):
        files.extend(glob.glob(os.path.join(root, patt)))
    return files

def change_ext(filename, newext):
    """Change file extension"""
    oldext = os.path.splitext(filename)[1]
    return re.sub(oldext+'$', newext, filename)

def default_testdir():
    """Default test directory is current directory of running script"""
    return os.path.dirname(os.path.realpath(__file__))

def script_path(filename):
    """Returns full-path to script (Python/Scripts)"""
    return os.path.join(_instlog.SCRIPTS_DIR, filename)

################################################################################

class NanoLPTestCase(ut.TestCase):
    def __init__(self):
        ut.TestCase.__init__(self) #, 'run')
        self.longMessage = True
        #self.maxDiff = None

    #def assertBufsEqual(self, buf1, buf2, msg):
        #pass

################################################################################

class TestExampleFile(NanoLPTestCase):
    """Test parsing of example.* file:
    1. Run nlp.py -i example.* if no example.sh otherwise use it as cmdline args
    2. If exists example.stderr, check stderr of run with example.stderr (as regexp)
    """
    def __init__(self, filename):
        NanoLPTestCase.__init__(self)
        self.indir = os.path.dirname(filename)
        self.filename = filename

    def runTest(self, *args):
        shfile = change_ext(self.filename, '.sh')
        args = [sys.executable, script_path("nlp.py")]
        if os.path.exists(shfile):
            # XXX no spaces in path!!!!
            args = args + core.fread23(shfile).split()
        else:
            args = args + ["-i", self.filename]
        proc = subprocess.Popen(args, stderr=subprocess.PIPE)
        exitcode = proc.wait()
        stderrbuf = core.bytestostr23(proc.stderr.read()).strip('\n')

        if exitcode != 0 or len(stderrbuf) != 0:
            err = os.path.splitext(self.filename)[0] + '.stderr'
            if os.path.exists(err):
                errbuf = readfile(err)
                self.assertRegexpMatches(stderrbuf, errbuf, msgfmt('unexpected exception'))
            else:
                self.fail('Exit with 1, stderr="%s"'%stderrbuf)

################################################################################

class TestExampleDirOuts(NanoLPTestCase):
    """Test matching contents of *.master files and it's original in
    example directory
    """
    def __init__(self, indir=''):
        NanoLPTestCase.__init__(self)
        self.indir = indir if indir else os.getcwd()

    def runTest(self, *args):
        for master in globfiles(self.indir, '*.master'):
            sys.stderr.write(msgfmt('%s', master, caption='MASTERFILE'))
            mbuf = readfile(master)
            out = os.path.splitext(master)[0].replace('__', os.sep)
            obuf = readfile(out)
            self.assertMultiLineEqual(mbuf, obuf,
                    msgfmt("out does not match '%s'", master))

################################################################################

class TestExamplesDir(ut.TestSuite):
    """TestSuite for example directory"""
    indir = ''
    def __init__(self, indir='', modpath=''):
        """Modpath is __file__ of caller module"""
        ut.TestSuite.__init__(self)
        if not indir:
            if modpath:
                indir = os.path.dirname(os.path.realpath(modpath))
            else:
                raise ValueError('indir or modpath should be setted')

        self.indir = indir
        rmoutfiles(self.indir)
        # create files from *.in files
        for infile in globfiles(self.indir, '*.in'):
            process_infile(self.indir, infile)
            #f = change_ext(in_, '')
            #shutil.copyfile(in_, f)
        # obtain extensions of testes examples from cfg file
        os.chdir(self.indir)
        core.Lp()
        # now parsers are configured via cfg file (see os.chdir())
        example_exts = []
        for p in core.Parser.parsers:
            example_exts.extend(p.ext)

        tests = []
        sys.stderr.write(msgfmt("'%s'"%self.indir, caption='TESTDIR'))
        for example in globfiles(self.indir, 'example.*'):
            name = os.path.split(example)[1]
            if name.count('.') > 1:
                # has more then one extension - possible master or out file
                continue
            ext = os.path.splitext(example)[1]
            if ext not in example_exts:
                continue
            tests.append(TestExampleFile(example))
            #sys.stderr.write("\nAdded example test '%s'"%example)
        tests.append(TestExampleDirOuts(self.indir))
        self.addTests(tests)

################################################################################

class TestDocStrings(ut.TestSuite):
    """TestSuite for docstrings in lp module"""
    def __init__(self):
        ut.TestSuite.__init__(self)
        # to use in doctests class names without package prefix:
        globals = {}
        globals.update(lp.__dict__)
        # modules to test with docstrings
        for mod in DOCTESTMODULES:
            sys.stderr.write(msgfmt("'%s' module"%mod.__name__, caption='DOCTESTS'))
            self.addTests(dt.DocTestSuite(mod, globs=globals, optionflags=dt.IGNORE_EXCEPTION_DETAIL))

################################################################################

class TestExamplesDirViaHTTP(TestExamplesDir):
    """Like TestExamplesDir but first run HTTP server to serve
    all files in example dir"""
    ## login name for authorization
    login = None
    ## password for authorization
    password = None
    def __init__(self, indir='', modpath='', auth=core.UNDEFINED):
        """modpath - module path (__file__), auth - 'login:password' or None to anonymous
        authorization"""
        TestExamplesDir.__init__(self, indir, modpath)
        if auth is core.UNDEFINED:
            self.login = _testcfg.HTTP_LOGIN
            self.password = _testcfg.HTTP_PASSWORD
        elif auth:
            self.login, self.password = auth.split(':')
    def run(self, results):
        args = [sys.executable, "-m", 'nanolp.test.httpserver', '--host=%s'%_testcfg.HTTP_HOST,
                '--port=%d'%_testcfg.HTTP_PORT, '--dir=%s'%self.indir]
        if self.login:
            args.extend(['--login=%s'%self.login, '--password=%s'%self.password])
        proc = subprocess.Popen(args, cwd=self.indir)
        time.sleep(_testcfg.HTTP_START_TIME)
        ret = TestExamplesDir.run(self, results)
        proc.kill()
        return ret

################################################################################

class TestExamplesDirViaFTP(TestExamplesDir):
    """Like TestExamplesDir but first run FTP server to serve
    all files in example dir"""
    ## login name for authorization
    login = None
    ## password for authorization
    password = None
    def __init__(self, indir='', modpath='', auth=core.UNDEFINED):
        """modpath - module path (__file__), auth - 'login:password' or None to anonymous
        authorization"""
        TestExamplesDir.__init__(self, indir, modpath)
        if auth is core.UNDEFINED:
            self.login = _testcfg.FTP_LOGIN
            self.password = _testcfg.FTP_PASSWORD
        elif auth:
            self.login, self.password = auth.split(':')
    def run(self, results):
        args = [sys.executable, "-m", 'nanolp.test.ftpserver', '--host=%s'%_testcfg.FTP_HOST,
                '--port=%d'%_testcfg.FTP_PORT, '--dir=%s'%self.indir]
        if self.login:
            args.extend(['--login=%s'%self.login, '--password=%s'%self.password])
        proc = subprocess.Popen(args, cwd=self.indir)
        time.sleep(_testcfg.FTP_START_TIME)
        ret = TestExamplesDir.run(self, results)
        proc.kill()
        return ret

################################################################################

def run(tests):
    """Called by some test-module in test/ dir"""
    runner = ut.TextTestRunner()
    runner.run(tests)

################################################################################
