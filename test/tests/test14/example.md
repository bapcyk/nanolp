title:      Example code
prev_title: Extensions
prev_url:   index.html
next_title: Abreviation Extension
next_url:   abbreviations.html
<<file.x, out.out>> `<<=c.*, join:\n>>`

Example of Literate Programming in Markdown
===========================================

<<on.Cmd, gpath:c.f1, do.define:upper $chunktext>>
<<on.Cmd.define, gpath:c.f2, do:lower $chunktext>>
<<on.Cmd.paste, gpath:c.f4, do:upper $chunktext>>

Code 1
------

First chunk <<c.f1>> `should be upper` and next <<c.f2>>:

    SHOULD BE LOWER

another <<c.f3, do.define:title $chunktext>> `should be title`.
Increment is <<inc>>: `$v += 1`.
Yet <<c.f4>>:

    def f(n):
        <<=inc, v:n>>
        return n

And <<c.f5, do.paste:title $chunktext>>:

    def f(n):
        <<=inc, v:n>>
        return n

Next is the example of arguments substitution handling:
<<enum, do.subargs:joinargs -c u -j '\, ' $value>> `$*`. And usage:
<<c.enum>>: `<<=enum, a, b, c>>`
