# Fetchers
#
# Author: Balkansoft.BlogSpot.com
# GNU GPL licensed

import re
import os
import io
import sys
import base64
import zipfile
import subprocess
from ftplib import FTP
import nanolp.core as core

class FSfile(core.Vfile):
    """Local FS fetcher"""
    descr = '<path>'
    scheme = r'(?!\w{2,}:)'

    def fetch(self, parser=None):
        return None
core.Vfile.register(FSfile)

################################################################################

class FSURLfile(core.Vfile):
    """Local FS via 'file:///...'
    """
    descr = 'file:///<path>'
    scheme = 'file://(localhost)?/'

    def fetch(self, parser=None):
        return None
core.Vfile.register(FSURLfile)

################################################################################

class HTTPfile(core.Vfile):
    """HTTP fetcher for 'http://...'
    """
    descr = 'http://<url><:port?>/<path>'
    scheme = 'http://'

    def fetch(self, parser=None):
        file = None; buffer = None
        try:
            # first get login, password
            if parser and parser.engine:
                urlopts = parser.engine.urlcfgfile.urlopts(self.orig_uri.url) or {}
            else:
                urlopts = {}
            login = urlopts.get('login', '') #.encode('utf8')
            password = urlopts.get('password', '') #.encode('utf8')
            # Create request instance
            request = core.UrlRequest(self.orig_uri.url)
            auth = '%s:%s'%(login, password)
            try:
                auth = base64.standard_b64encode(auth)
            except TypeError:
                auth = base64.standard_b64encode(auth.encode()).decode()
            request.add_header("Authorization", "Basic %s"%auth)   
            file = core.urlopen(request)
            buffer = file.read()
        finally:
            if file:
                try: file.close()
                except: pass
        return (None, buffer)
core.Vfile.register(HTTPfile)

################################################################################

class FTPfile(core.Vfile):
    """FTP fetcher for 'ftp://...'
    """
    descr = 'ftp://<url><:port?>/<path>'
    scheme = 'ftp://'

    def fetch(self, parser=None):
        url = re.sub('ftp://', '', self.orig_uri.url, flags=re.I)
        m = re.match('(.+?)(:\d+)?/(.+)', url, re.I)
        if not m:
            raise ValueError("Wrong formed URL '%s'"%self.orig_uri.url)
        host = m.group(1)
        port = m.group(2).lstrip(':') if m.group(2) else '21'
        path = m.group(3)
        if parser and parser.engine:
            urlopts = parser.engine.urlcfgfile.urlopts(self.orig_uri.url) or {}
        else:
            urlopts = {}
        login = urlopts.get('login', '') #.encode('utf8')
        password = urlopts.get('password', '') #.encode('utf8')
        ftp = None; buffer_io = None; buffer = None
        try:
            port = int(port)
            ftp = FTP()
            ftp.connect(host, port)
            ftp.login(login, password)
            buffer_io = io.BytesIO()
            ftp.retrbinary('RETR %s'%path, buffer_io.write)
            buffer = buffer_io.getvalue()
        finally:
            if ftp:
                try: ftp.quit()
                except: pass
            if buffer_io:
                try: buffer_io.close()
                except: pass
        return (None, buffer)
core.Vfile.register(FTPfile)

################################################################################

class SHELLfile(core.Vfile):
    """Shell pipe fetcher for 'shell://...'. All executables should be placed in
    extradir. (usually 'nanolp-extra/') or it may be python.exe
    """
    descr = 'shell:<path-to-exec>#<options>'
    scheme = 'shell:'
    unsafe = True

    def fetch(self, parser=None):
        p = core.url2path(self.orig_uri.url, fragments=True)
        exename = p[0]
        cmdline = p[1] if len(p) > 1 else ''
        # normalization of exename path
        normpath = lambda p: os.path.normpath(os.path.normcase(p)) # used below
        exename = normpath(exename)
        # Check that exec is located in right place
        secure = False
        if normpath(sys.executable) == exename:
            # it's python exe file
            secure = True
        else:
            # something else
            exename = core.extrapath(exename)
            if os.path.exists(exename):
                # it's existent in extradir. 
                secure = True
        # so, if insecure
        if not secure:
            raise RuntimeError("Insecure URL '%s'"%self.orig_uri.url)
        # Run and read
        args = [exename] + cmdline.split()
        proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        exitcode = proc.wait()
        stdoutbuf = proc.stdout.read()
        return (None, stdoutbuf)
core.Vfile.register(SHELLfile)

################################################################################

class ZIPfile(core.Vfile):
    """ZIP fetcher for 'zip://...'
    """
    descr = 'zip:<path-to-zip>#<path-in-zip>'
    scheme = 'zip:'

    def fetch(self, parser=None):
        p = core.url2path(self.orig_uri.url, fragments=True)
        if len(p) != 2:
            raise ValueError("Wrong formed URL '%s'"%self.orig_uri.url)
        zipfname, fname = p
        if parser:
            zipfname = parser.ensureinput(zipfname)
        # Open and read. Obtain options first
        if parser and parser.engine:
            urlopts = parser.engine.urlcfgfile.urlopts(self.orig_uri.url) or {}
        else:
            urlopts = {}
        # password is string, convert to bytes, but if is empty, set to None (not used)
        password = urlopts.get('password', '').encode('utf8')
        if not password: password = None
        # opening zip file and read what is need
        with zipfile.ZipFile(zipfname, 'r') as zip:
            fileinfo = zip.getinfo(fname)
            buffer = zip.read(fname, password)
        # prepare file metainfo
        name = os.path.basename(fname)
        ext = os.path.splitext(name)[1]
        atime = core.VfileInfo.mkst_time(fileinfo.date_time)
        mtime = core.VfileInfo.mkst_time(fileinfo.date_time)
        mode = (fileinfo.external_attr >> 16) & 0x1FF # & 0777
        fileinfo = core.VfileInfo(fmt=ext, name=name, mode=mode, atime=atime, mtime=mtime)
        return (fileinfo, buffer)
core.Vfile.register(ZIPfile)
