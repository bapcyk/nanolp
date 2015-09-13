# Nano LP -- Literate Programming tool #

- Project HOME http://code.google.com/p/nano-lp/
- Presentation http://nano-lp.googlecode.com/files/present.pdf
- Documentation http://code.google.com/p/nano-lp/w/list
- Discussion http://groups.google.com/group/nano-lp-discuss
- ChangeLog http://code.google.com/p/nano-lp/wiki/Changes

## Introduction ##

It's new literate programming (LP) tool. Main idea is too avoid processing
document (LP source) format, so input document format is supported by it's
traditional external tool. So it's possible to have favourite workflow: WYSIWYG
editing/text processing/converting with you favourite tool/suite
(OpenOffice/Markdown tool/TeX/etc.).

At the moment, supported input formats are:

- Markdown/MultiMarkdown
- OpenOffice/LibreOffice
- Creole
- reStructuredText
- TeX/LaTeX
- Txt2Tags
- Asciidoc
- HTML/XML
- ... and any compatible

Supported schemes are:

- FSfile - `<path>`
- FSURLfile - `file:///<path>`
- HTTPfile - `http://<url><:port?>/<path>`
- FTPfile - `ftp://<url><:port?>/<path>`
- SHELLfile - `shell:<path-to-exec>##<options>`
- ZIPfile - `zip:<path-to-zip>##<path-in-zip>`

with crypting (ZIP), authorizing (FTP, HTTP).

## Main features ##

- definition of command (macros) with placeholders in the body (code chunk)
- variables dictionaries (for substitution of placeholders)
- pasting command code chunk with substitution of placeholders
- definition of multiple parts code-chunks (for wrapping, etc.)
- joining, 'ending', etc. several code chunks
- 'globbing' commands when paste
- including one file to another (library)
- custom surround symbols (different for doc and code)
- custom event handlers (filters in chain/pipe manner)
- supporting URLs in file names (read via HTTP)
- prepare of HTML files (with LP commands) for Web publishing
- generating cross-references file
- auto-detecting of cycles
- configurable via simple .INI like file
- works with Python 2.7 - Python 3+
- works with Unicode (UTF8) 
- highly extendible

## Installation ##

Install Python (2.7 or 3+) first, then run

```
    $ python setup.py install
```

Then run

```
    $ nlp.py -h
```

or

```
    $ python path-to-scripts/nlp.py -h
```
