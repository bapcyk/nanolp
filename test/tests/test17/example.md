Includes [[use, mnt:c, zip\:cstd.zip#a/b/cstd.odt]],
[[use, mnt:m, zip\:m/math.zip#a/b/math.md]],
[[use, mnt:cat, fmt:md, shell\:c\:\\python33\\python\.exe#-m nanolp.test.cat c\:\\prj\\nanolp\\src\\test\\tests\\test17\\cat\.txt]]

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
    [[=m.min]]

    [[=cat.abs]]

not code
not code

Lalalalalalal
Lalalalalalal
