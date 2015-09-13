title:      Example code
[[file.x, out.out]] `[[=c.fun1]]`

Пример
======

Код 1
-----

Test if variable is negative looks like [[c.isneg]]: `if $x < 0`.
So, we can write absolute function [[c.fun1]]:

    def fun1(x):
        # комментарий
        [[=c.isneg, x:a]]:
            a += 100
            return -a
        else:
            return a

not code
not code

Lalalalalalal
Lalalalalalal
