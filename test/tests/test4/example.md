title:      Example code

Example of simple math library
==============================

Files
-----

This is the dummy math. library in C. Header file is [[file.h, m.h.out]]:

    [[=incl.*]]
    [[=decl.*, join:;\n]];

Source file is [[file.c, m.c.out]]:

    #include "m.h"
    [[=decl.abs]]
    {
        [[=c.abs]]
    }
    [[=decl.max]]
    {
        [[=c.max]]
    }

Source
------

Negative testing [[c.isneg]] of some variable is very simple: `$v < 0`.
So, owr function will have signature [[decl.abs]]: `int abs(int x)`.
Its body [[c.abs]] is simple:

    if ([[=c.isneg, v:x]]) return -x;
    else return x;

We need to include files [[incl.stdio]]:

    #include <stdio.h>
    #include <math.h>

Also we can declare very simple function: [[decl.max]]: `int max(int x, int y)`,
which can be defined easy [[c.max]]:

    if (x>y) return x;
    else return y;
