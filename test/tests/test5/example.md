Some very simple example
========================

Considering we want to write C module [[file.abs, out.out]] for calculating absolute value of number with implementation of this function: `[[=fn.abs]]`, nothing else.
Implementation of this function is simple, but first let's show [[isneg]] testing of negative value: `$v<0` - if number is smaller then 0 then it's negative.
OK, now, here is the function [[fn.abs]] (with empty line in the body):

    int abs(int x) {

        if ([[=isneg, v:x]]) return -x;
        else return x;


        // last line


    }

That's all.
