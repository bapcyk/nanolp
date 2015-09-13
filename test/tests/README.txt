Files tests
===========

There are several directories in the tests/ (test1, test2, etc.)
with file-based tests - for test of parsing, cross-reference
creation, publishing and so on.

To run them, do:

    python -m unittest discover -s test/tests

or

    python -m unittest discover test/tests/test<N>

If you need demo files, see tests! Each parsable file (usually they
looks like example.*, note also relative files, included with <<use>>
command!) - is also for demonstration or little tutorial.

Each directory is one or more tests actually. If it's a test of
parsing, example.* should exist there. Usually test engine try to
parse some example-file and then to compare all SOME.master files with
their reflections: considering SOME file. Test is successful, if
comparision is true.

If there is *.sh files, instead of parsing example files (running
nlp.py tool as -i EXAMPLE) nlp.py command with option from sh-file
will be executed.

So, usually example.* files are main "material" for testing (if no
*.sh files).

If exists *.in files, they use as original for file with the same
name, but without .in extension (SOME.in -> SOME).

*.in files
==========

Sometimes text in *.master files depends on system (OS, file system,
so on). In this case *master file (or another file) must be modified
before test running. It's accomplished by creating of target file from
original *.in file:

    SOME-NAME.SOME-EXTENSION.in -> SOME-NAME.SOME-EXTENSION

but with substitution of place-holders in *.in file. They are in
format:

    $SOMETHING

or:

    ${SOMETHING SELECTOR}

or even:

    ${SOMETHING SELECTOR|...}

First is usual substitution of special variable with it's value.
Some of these variables are from test module (see 'nanolp.test.cases'),
other - from core (see 'nanolp.core') and so on...
Second is the substitution with value selected from some common entity
(imagine dictionary) and third is the substitution with pipes: next
SOMETHING get as value result of previous substitution OR with own
SELECTOR if no previous result.

Escaping in command
===================

Symbols * , : \ has special meaning in command, so they should be
escaped with \. In test is used total substitution of ALL symbols from
Python string.punctuation set, but is needed only these.

For example:

    <<come_cmd, some_arg:http\://some-url>>

Note \ before : in 'http\://some-url'.

Auto-cleaning before testing
============================

Before to run any test all outputs are deleted, i.e. all files with
names like of *.master files but without .master extension. Usually
resulting extension is .out, but not always!

Output file may be in different directory with test directory. In this
case master-file looks like somedir__somefile.master, so two
underscores '__' will be replaced by File System path separator: '__'
-> '/', and out file in our example becames: somedir/somefile
(directory will be create if not exists).

Also all *.in files are processed and all place-holders are
substituted.

Driver module is still testSOMETHING.py. What really will happens is
determined by this Python module.

Each file-based test has own config file - lprc. And these lprc files
usually are different for different tests! Also may be custom lpurlrc
config file - configuration of URLs.
