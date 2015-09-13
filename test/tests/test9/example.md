title:      Example code
prev_title: Extensions
prev_url:   index.html
next_title: Abreviation Extension
next_url:   abbreviations.html
Include:    [[use, mnt:c, cstd.odt]]
Write to:   [[file.x, out.out]] `[[=c.fun1]]`

Example of Literate Programming in Markdown
===========================================

Code 1
------

This example shows using of external file also.
Test if variable is negative looks like [[c.isneg]]: `if $x <
0`.
So, we can write absolute function [[c.fun1]]:

    [[=c.hh.0, file:GUI]]
    def fun1(x):
        [[=c.isneg, x:a]]:
            a += 100
            return -a
        else:
            return a
    [[=c.hh.1]]

not code
not code

Lalalalalalal
Lalalalalalal
