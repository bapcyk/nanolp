Introduction
============

NanoLP package contains different tests in test/ directory. Testing
"engine" is based on UnitTest framework, so all test has bound
testSOMETHING.py module in it's directory.

Docstrings tests
================

Some modules of nanolp package contains docstring based tests
(doctests). To run it, do from directory of decompressed
source-package:

    python -m unittest discover -s test/

Bound Python module is testDocStrings.py in test/ directory with
corresponding config file lprc.

Files tests
===========

Are placed in tests/ subdirectory.
