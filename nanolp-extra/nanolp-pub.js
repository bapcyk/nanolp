/// traverse DOM
function walk(func, node, acc) {
    if (typeof acc == 'undefined')
        acc = new Array();
    acc = func(acc, node);
    node = node.firstChild;
    while(node) {
        walk(func, node, acc);
        node = node.nextSibling;
    }
    return acc;
}

/// escaping function
RegExp.quote = function(str) {
    return (str+'').replace(/([.?*+^$[\]\\(){}|-])/g, "\\$1");
};

/// creates regexp for <<cmd>>
function defineRegExp() {
    var lSur = RegExp.quote(LP_CFG['SURR'][0]);
    var rSur = RegExp.quote(LP_CFG['SURR'][1]);
    return new RegExp(lSur + '([^=]+?)(,.*?)?' + rSur, 'g');
}

/// creates regexp for <<=cmd>>
function pasteRegExp() {
    var lSur = RegExp.quote(LP_CFG['SURR'][0]);
    var rSur = RegExp.quote(LP_CFG['SURR'][1]);
    return new RegExp(lSur + '=(.+?)(,.*?)?' + rSur, 'g');
}

var defineRe = defineRegExp();
var pasteRe = pasteRegExp();

function _replDefine(g0, g1, g2) {
    if (g2 == undefined) g2 = '';
    var s = '<a name="@1"><span class="lpdefine">(@1@2)</span></a>';
    return s.replace(/@1/g, g1).replace(/@2/, g2);
}

function _replPaste(g0, g1, g2) {
    _cmdUrl = function(cmdPath) {
        var srcFile = LP_CFG['CMDS'][cmdPath];
        if (srcFile == '') {
            return '#' + cmdPath;
        } else if (/.htm$|.html$|.shtml$/.test(srcFile)) {
            // HTML source file of defined chunk
            return srcFile + '#' + cmdPath;
        } else {
            return srcFile;
        }
    }

    if (g2 == undefined) g2 = '';
    if (-1 != g1.indexOf('*')) {
        // some glob
        var s = '<span class="popup">='+g1+g2+'<div><span id="caption">Matched:</span>';
        var re = new RegExp(glob2re(g1));
        for (var cmdPath in LP_CFG['CMDS']) {
            if (re.test(cmdPath)) {
                var dsuff = /\.-?\d+$/.exec(cmdPath);
                if (dsuff) {
                    // finished with '.DIGITS', found ref will ends with the same
                    // numeric suffix, so cut it, bcz in HTML is only parent chunk,
                    // i.e. 'xxx' instead of 'xxx.0', 'xxx.1'...
                    var ref = _cmdUrl(cmdPath).slice(0, dsuff['index']+1);
                } else {
                    var ref = _cmdUrl(cmdPath);
                }
                s += '<a href="@1">@2</a>'.replace(/@1/, ref).replace(/@2/, cmdPath);
            }
        }
        s += '</div></span>';
        return s;
    }
    else {
        var s = '<a href="@1">=@2@3</a>';
        return s.replace(/@1/, _cmdUrl(g1)).replace(/@2/, g1).replace(/@3/, g2);
    }
}

/// on visit DOM node
function visitDefine(acc, node) {
    var txt = node.innerHTML;
    if (txt) {
        txt = txt.replace(defineRe, _replDefine);
        node.innerHTML = txt;
    }
    return acc;
}

function visitPaste(acc, node) {
    var txt = node.innerHTML;
    if (txt) {
        txt = txt.replace(pasteRe, _replPaste);
        node.innerHTML = txt;
    }
    return acc;
}

/** Translate a shell PATTERN to a regular expression.
  * Adapted from Python
  * There is no way to quote meta-characters */
function glob2re(pat) {
    var i = 0;
    var n = pat.length;
    var res = '';
    while (i < n) {
        var c = pat[i];
        i = i+1;
        if (c == '*')
            res = res + '.*';
        else if (c == '?')
            res = res + '.';
        else if (c == '[') {
            var j = i;
            if (j < n && pat[j] == '!')
                j = j+1;
            if (j < n && pat[j] == ']')
                j = j+1;
            while (j < n && pat[j] != ']')
                j = j+1;
            if (j >= n)
                res = res + '\\[';
            else {
                //stuff = pat[i:j].replace('\\','\\\\');
                var stuff = pat.slice(i, j).replace('\\','\\\\');
                i = j+1;
                if (stuff[0] == '!')
                    stuff = '^' + stuff.slice(1);
                else if (stuff[0] == '^')
                    stuff = '\\' + stuff;
                res = res + '[' + stuff + ']';
                //res = '%s[%s]' % (res, stuff);
            }
        }
        else
            res = res + RegExp.quote(c);
    }
    return res; // + '\Z(?ms)';
}

window.onload = function() {
    var body = document.body;
    /// XXX really replace once - all occurs in body.innerHTML
    var res;
    res = walk(visitDefine, body);
    res = walk(visitPaste, body);
}
