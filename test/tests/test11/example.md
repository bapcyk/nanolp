title:      Example code
prev_title: Extensions
prev_url:   index.html
next_title: Abreviation Extension
next_url:   abbreviations.html
<<file.x, md.out>> `<<=c.fun1>>`

Example of Literate Programming in Markdown
===========================================

Code 1
------

Test if variable is negative looks like <<c.isneg>>: `if $x < 0`.
So, we can write absolute function <<c.fun1>>:

    def fun1(x):
        <<=c.isneg, x:a>>:
            a += 100
            return -a
        else:
            return a
    x = 1
