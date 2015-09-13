<<file.x, out.out>> `<<=vartest>>`

All variables are bound before processing all chunks.
Other words, when chunks are processing, variables
are bound.

<<vars, v1:1, v2:2>>
<<vars, v3:3>>
<<vars, d1, v1:10, v2:20>>

Some snippet <<snip1>>: `v1 is $v1, v2 is $v2`.
And snippet <<snip2>>: `$0, $1, $-1, $*`.
Test of variable dictionaries: <<vartest>>:

    <<=snip1>>
    <<=snip1, v1:100>>
    <<=snip1, *:*>>
    <<=snip1, *:$d1>>
    <<=snip1, *:$d1, v1:0>>
    $v1
    ${d1.v1}
    $v1.x
    $v3
    <<=snip2, a, b>>
