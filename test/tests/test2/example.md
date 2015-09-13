title:      Example code
prev_title: Extensions
prev_url:   index.html
next_title: Abreviation Extension
next_url:   abbreviations.html
@@file.some, out.out@@ `@@=c.fun1@@`

Example of Literate Programming in Markdown
===========================================

Code 1
------

Test if variable is negative looks like @@c.isneg@@: `if $x < 0`.
Next is demonstration of args suppressing, @@c.add100@@: `$a += 100`.
So, we can write absolute function @@c.fun1@@:

    def fun1(x):
        @@=c.isneg, x:a@@:
            @@=c.add100, *:*@@
            return -a
        else:
            return a

not code
not code

Lalalalalalal
Lalalalalalal
