# -*- coding: utf-8 -*-
import os
from datetime import datetime
from HTMLParser import HTMLParser
from itertools import compress
from operator import itemgetter

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ' '.join((' '.join(self.fed)).split())

def remove_tag(start, end, html, replace_with=' '):
    while start in html and end in html:
        remove_start = html.find(start)
        remove_end = html.find(end,remove_start)+len(end)
        remove_string = html[remove_start:remove_end]
        html = html.replace(remove_string, replace_with)
    return html

def strip_tags(html, keep_image=True):
    html = html.replace(u'&amp;', u'~!~')     # ampersand
    html = html.replace(u'&#10004;', u'~!!~') # checkmark
    if keep_image:
        html = html.replace(u'<img', u'~img~') # image    
    html = remove_tag(u'<tr', u'>', html, '')
    html = remove_tag(u'</tr', u'>', html, u'~newline~')
    html = remove_tag(u'<th', u'>', html, '')
    html = remove_tag(u'</th', u'>', html, u'~newline~')
    html = remove_tag(u'<style>', u'</style>', html)
    html = remove_tag(u'<script', u'</script>', html)
    s = MLStripper()
    s.feed(html)
    s = s.get_data()
    s = s.replace(u'~!~', u'&').replace(u'~!!~', u'\u2713')
    if keep_image:
        s = s.replace(u'~img~', u'<img')
    s = s.split()
    s = ' '.join(s).replace(u'~newline~', '\n')
    s = '<br>'.join([line.strip() for line in s.split('\n')])
    return s

def toUc(inp):
    if isinstance(inp, unicode):
        return inp
    try:
        inp = unicode(inp, encoding='utf-8')
    except:
        print "Can't convert to unicode:", inp
    return inp

def print_output(inp, lbl, app):
    outp = inp
    try:
        lbl.clear()
        if not isinstance(outp, basestring):
            outp = unicode(outp)
        lbl.setText(outp)
        app.processEvents()
    except:
        pass
    finally:
        no_print = [u'Processing', u'modified', u'Questionnaire parsed', u'Please', u'Export Complete', u'to save', u'to export']
        # if all([item not in outp for item in no_print]): print outp

def save_filename(fl,fld):
    '''fl comes in with the extension'''
    if fl not in os.listdir(fld):
        fl = os.path.join(fld,fl)
    else:
        name = u'.'.join(fl.split(u'.')[:-1])
        ext = fl.split(u'.')[-1]
        i = 1
        while True:
            fl = u'{}_{}.{}'.format(name,i,ext)
            if fl not in os.listdir(fld):
                fl = os.path.join(fld,fl)
                break
            i += 1
    return fl

def opn(inp):
    if u'..' not in inp: return inp
    inp = inp.split(u',')
    outp = []
    for item in inp:
        if u'..' not in item:
            outp.append(item)
        else:
            dum = item.split(u'.')
            start_ind = int(dum[0])
            end_ind = int(dum[-1])+1
            if abs(end_ind - start_ind) > 1130:
                return
            ext = ','.join([str(n) for n in range(start_ind,end_ind)])
            if ext: outp.append(toUc(ext))
    outp = u','.join(outp)
    return outp

def open_codes(inp, real=False):
    '''if real=False, takes a string like 1,2..5,7,10..12 and returns 1,2,3,4,5,7,10,11,12 in unicode.
                      If no .. is in string it returns it as it is but unicode
                      If the string is like [r1.c1];[r2.c2] with c1,c2 like 1,2..5,7,10..12 it returns [r1.c1];[r2.c2] with c1,c2 opened like above.
       if real=True, takes a string like 1.2,2.1..5,DK and returns [1.2, [2.1, 5.0], DK] no numeric items as unicode, numerics as floats.
                     If no .. is in string it returns it as it is but unicode'''
    inp = toUc(inp)
    if not real:
        if u'[' not in inp:
            outp = opn(inp)
        else:
            inp = inp.split(u';')
            outp = []
            for item in inp:
                part1 = item.split(u'.')[0][1:]
                part2 = u'.'.join(item.split(u'.')[1:])[:-1]
                outp.append(u'[{}.{}]'.format(part1, opn(part2)))
            outp = u';'.join(outp)
    else:
        outp = []
        inp = inp.split(u',')
        for item in inp:
            if u'..' not in item:
                new_item = item
                try:
                    new_item = float(item)
                    outp.append(new_item)
                except:
                    outp.append(toUc(str(new_item)))
            else:
                t, f = [part[::-1] for part in item[::-1].split(u'..')]
                outp.append([float(f), float(t)])
    return outp

def date_str(date):
    days = {0:u'Monday', 1:u'Tuesday', 2:u'Wednesday', 3:u'Thursday', 4:u'Friday', 5:u'Saturday', 6:u'Sunday'}
    months = {1:u'January',2:u'February',3:u'March',4:u'April',5:u'May',6:u'June',7:u'July',8:u'August',9:u'September',10:u'October',11:u'November',12:u'December'}
    dt = datetime.strptime(date, '%Y%m%d')
    dt_str = u'{} {} {} {}'.format(days[dt.weekday()], dt.day, months[dt.month], dt.year)
    return dt_str

def day_str(date):
    days = {0:u'Monday', 1:u'Tuesday', 2:u'Wednesday', 3:u'Thursday', 4:u'Friday', 5:u'Saturday', 6:u'Sunday'}
    date = datetime.fromtimestamp(date)
    return u'{}, {}'.format(days[date.weekday()], date.strftime('%d-%m-%Y %H:%M:%S'))

def display_time(seconds, granularity=5):
    intervals = (
        ('weeks', 604800),  # 60 * 60 * 24 * 7
        ('days', 86400),    # 60 * 60 * 24
        ('hours', 3600),    # 60 * 60
        ('mins', 60),
        ('secs', 1),
        )
    result = []
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])

def split_to_chunks(lst, inds):
    """This function takes as arguments a list of items and a list of indices (unique in ascending order).
       Returns a list of lists splitting the input list to chunks according to the indices.
       Args:
           lst: A list of items
           inds: A list of integers unique in ascending order
       Returns: List of lists
       Examples:
           [0,1,2,3,4,5,6,7,8,9], [5,4,7] -> []
           [0,1,2,3,4,5,6,7,8,9], [4.0,5,7] -> []
           [0,1,2,3,4,5,6,7,8,9], [4,4,7] -> []
           [0,1,2,3,4,5,6,7,8,9], [20,4,7] -> []
           [0,1,2,3,4,5,6,7,8,9], [4,5,6] -> [[0, 1, 2, 3], [4], [5, 6], [7, 8, 9]]
           [0,1,2,3,4,5,6,7,8,9], [0,1,7] -> [[0], [1, 2, 3, 4, 5, 6], [7, 8, 9]]
           [0,1,2,3,4,5,6,7,8,9], [0,1,9] -> [[0], [1, 2, 3, 4, 5, 6, 7, 8], [9]]"""
    val = []
    if inds == [] or (inds != [] and max(inds) >= len(lst)): return val
    if inds != sorted(inds):
        print_output('split_to_chunks: Indices must be in ascending order')
        return val
    if len(inds) != len(set(inds)):
        print_output('split_to_chunks: Indices must be unique')
        return val
    if not all([isinstance(ind, int) for ind in inds]):
        print_output('split_to_chunks: Indices must be integers')
        return val
    chunks = [lst[:inds[0]]]
    for i,ind in enumerate(inds):
        if i + 1 < len(inds):
            chunks.append(lst[inds[i]:inds[i+1]])
        else:
            chunks.append(lst[inds[-1]:])
    val = [chunk for chunk in chunks if chunk]
    return val

def select_rows(tb, mask, first_is_headers=True):
    """This function takes as arguments a list of lists(rows) as (table) input and a boolean list as mask with the same length of the table.
       Returns the rows of the corresponding indices WHERE 0 INDEX REFERS TO THE FIRST LIST IN tb.
       If first_is_headers=True and the first item of the mask is False, it is changed to True so that the headers is in the result
       Args:
           tb: A list of lists
           mask: A list of integers unique in ascending order
       Returns:
           A list of lists containing the selected rows and the headers (first row) if headers=True
    Example: tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [True,False,True], True -> [['a', 'b', 'c'], [4, 5, 6]]
             tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [True,False,True], False -> [['a', 'b', 'c'], [4, 5, 6]]
             tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [False,True,True], True -> [['a', 'b', 'c'], [1, 2, 3], [4, 5, 6]]
             tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [False,True,True], False -> [[1, 2, 3], [4, 5, 6]]
             tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [], False -> (Mask must be of the same length with the table) None
             tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [], True -> (Mask must be of the same length with the table) None
             tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], 4*[True], False -> (Mask must be of the same length with the table) None
             tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], 4*[True], True -> (Mask must be of the same length with the table) None"""
    if len(mask) != len(tb):
        print 'Mask must be of the same length with the table'
        return
    if first_is_headers and not mask[0]: mask[0] = True
    return list(compress(tb, mask))

def get_items(inds, lol):
    def my_itemgetter(row):
        r = itemgetter(*inds)(row)
        if not lol:
            return r
        else:
            if type(r) is tuple:
                return list(r)
            else:
                return [r]
    return my_itemgetter

def select_cols(table, cols, lol=True):
    """This function takes as arguments a list of lists(rows) as (table) input assuming that first row is headers
       and a list of strings as column names and returns a list of lists(rows) if lol=True or a list of strings if lol=False,
       THE FIRST BEING THE HEADERS and the rest the corresponding values.
       Args:
           tb: A list of lists
           column_names: A list of strings as column names
       Returns:
           A list of lists or a list of strings the first list being the headers and the rest the corresponding values"""
    cols_ = set(cols)
    len_cols = len(cols)
    inds = []
    # get indices of selected elements
    for i, var in enumerate(table[0]):
        if var in cols_:
            inds.append(i)
            if len(inds) == len_cols:
                break
    # get sublists with selected elements
#    iget = itemgetter(*inds)
    iget = get_items(inds, lol)
    return [iget(row) for row in table]

def select_cols_2(table, cols):
    cols_ = set(cols)
    # build selector list
    sel = [i in cols_ for i in table[0]]
    # get sublists with selected elements
    return [list(compress(i, sel)) for i in table]

def select_cols_3(tb, column_names):
    inds = [tb[0].index(cn) for cn in column_names]
    table = [[line[i] for i in inds] for line in tb]
    return table

def strip_fltr_tags(html):
    while u'<a href="fltr_' in html:
        remove_tag_start_1 = html.find(u'<a href="fltr_')
        remove_tag_end_1 = html.find(u'>', remove_tag_start_1)
        remove_tag_start_2 = html.find(u'</a>', remove_tag_end_1)
        string_to_replace = html[remove_tag_start_1:remove_tag_start_2+4]
        string_to_replace_with = html[remove_tag_end_1+1:remove_tag_start_2]
        html = html.replace(string_to_replace, string_to_replace_with)
    return html

css_style_and_head = u'''<style>
/* page layout */

#top{height:3em;
     width:100%;
     line-height:3em;
     background-color:#D2D2D2;}
#left{position:fixed;
      height:90%;
      width:12%;
      left:0px;
      top:0em;
      padding-left:1em;
      padding-right:1em;
      padding-top:1em;
      padding-bottom:5em;
      overflow-y:scroll;
      background-color:#E6E6E6;
      font-size:13px;z-index:2;}
#content{position:relative;
         top:0em;
         margin-left:14%;
         padding:0px 10px 10px 10px;z-index:1;}

/* tables layout */

	td, th{border:1px solid black;
               text-align:center;
               padding:3px;}
        td.row_labels{text-align:left;
                      min-width:20em;}
        th.header_base{background-color:#003D81;
                       font-weight:bold;
                       color:#ffffff;
                       text-align:left;}
        th.header_text{background-color:#D2D2D2;
                       font-weight:normal;
                       text-align:left;}
        tr:nth-child(even){background-color:#ededed;}
        tr.header_rest{background-color:#D2D2D2;}
        td.header_rest{background-color:#D2D2D2;}
        td.base_tot_cell{font-weight:bold;}
       .rb_cb_table{width:100%;}
        table.rb_cb_table td, table.rb_cb_table th{width:3%;}
       .rb_cb_cnts_prcs{min-width:12%;}
</style>
<head><meta charset="UTF-8"></head>'''

js_tags = u'''
<script>function toggle_all_func(){
    logics_tags = document.querySelectorAll("div.logics");
    toggle_all_tags = document.querySelectorAll("a.toggle_all_logs");
    toggle_this_tags = document.querySelectorAll("a.toggle_this_logs");
    if (toggle_all_tags[0].innerHTML === 'Hide All Logics ↑') {
      for (var i = 0; i < logics_tags.length; i++) {
        logics_tags[i].style.display = 'none';
        toggle_this_tags[i].innerHTML = 'Show Question Logics ↓';
        toggle_all_tags[i].innerHTML = 'Show All Logics ↓';
      }
    } else {
      for (var i = 0; i < logics_tags.length; i++) {
        logics_tags[i].style.display = 'block';
        toggle_this_tags[i].innerHTML = 'Hide Question Logics ↑';
        toggle_all_tags[i].innerHTML = 'Hide All Logics ↑';
      }
    }
  }
  
function toggle_this_func(el){
    this_logic = el.nextSibling.nextSibling.nextSibling;
    if (el.innerHTML === 'Hide Question Logics ↑') {
        el.innerHTML = 'Show Question Logics ↓'
        this_logic.style.display = 'none';
    } else {
      el.innerHTML = 'Hide Question Logics ↑'
      this_logic.style.display = 'block';
    }
}
</script>
'''

def make_html_doc(top_string=u'HELLENIC RESEARCH HOUSE', toc='', fltr=[], tables=[]):
    fltrs_num = len(fltr)
    fltr = u'({})'.format(' <u><b>&</b></u> '.join(fltr)) if fltrs_num > 1 else (u'{}'.format(' <u><b>&</b></u> '.join(fltr)) if fltrs_num == 1 else u'')
    html_doc = []
    html_doc.append(css_style_and_head)
    html_doc.append(u'<body>')
    html_doc.append(u'<div id="left"><div style="padding-right:5px;"><center><b>TABLE OF CONTENTS</b></center><hr><br></div>{}</div>'.format(toc))
    main_content = u'\n'.join([u'[<a href="#top">Go to top ↑</a>]&nbsp;&nbsp;&nbsp;'+ (fltr if fltrs_num > 0 else u'') + (u'&nbsp;&nbsp;&nbsp;<a href="fltr_OFF">Remove Filter</a>' if fltrs_num > 0 else u'') + (u'&nbsp;&nbsp;&nbsp;<a href="fltr_OFF_ALL">Remove All Filters</a>' if fltrs_num > 1 else u'') + table for table in tables])
    html_doc.append(u'<div id="content"><div id="top"><center><b>{}</b></center></div><br><br>{}</div>'.format(top_string, main_content))
    html_doc.append(js_tags)
    html_doc.append(u'</body>')
    return ''.join(html_doc)

class UnaryOperation(object):
    def __init__(self, tokens):
        self.operator, self.operand = tokens[0]
class BinaryOperation(object):
    def __init__(self, tokens):
        self.operator = tokens[0][1]
        self.operands = tokens[0][0::2]

class SearchNot(UnaryOperation):
    def to_str(self):
        op_str = self.operand.to_str()
        if any([c in op_str for c in u'~&|']):
            return u'{}({})'.format(self.operator, op_str)
        else:
            return u'{}{}'.format(self.operator, op_str)
    def eval(self):
        return [not x for x in self.operand.eval()]

class SearchAnd(BinaryOperation):
    def to_str(self):
        return u'&'.join([opnd.to_str() for opnd in self.operands])
    def eval(self):
        return list_wise_op(all, [op.eval() for op in self.operands])

class SearchOr(BinaryOperation):
    def to_str(self):
        return u'|'.join([opnd.to_str() for opnd in self.operands])
    def eval(self):
        return list_wise_op(any, [op.eval() for op in self.operands])

class ConditionString(object):
    def __init__(self, tokens, qns):
        self.term = tokens[0]
        splited = self.term.split(u':')
        self.qn_name = splited[0]
        self.fltr = u':'.join(splited[1:])
        self.qn = [qn for qn in qns if qn.name == self.qn_name][0]
    def to_str(self):
        return self.term.replace(self.qn_name, u'<a href="#{}">{}</a>'.format(self.qn_name, self.qn_name))
    def eval(self):
        return self.qn.filter_data(self.fltr)

def list_wise_op(op, operands):
    return [op(a_b) for a_b in zip(*operands)]


if __name__ == '__main__':
#    tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [True,False,True], True
#    tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [True,False,True], False
#    tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [False,True,True], True
#    tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [False,True,True], False
#    tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [], False
#    tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], [], True
#    tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], 4*[True], False
#    tb, mask, headers = [['a','b','c'],[1,2,3],[4,5,6]], 4*[True], True
#    print select_rows(tb, mask, headers)
#    print list(compress([], []))


#    import time
#    let = u'abcdefghijklmnopqrstuvwxyz'
#    rng = range(0,100)
#    cols = [u'{}_{}'.format(c,i) for i in rng for c in let]
#    rng = range(10,31)
##    rng = range(10,101)
#    col_names = [u'{}_{}'.format(c,i) for i in rng for c in let]
#    lines = 1000
#    tb = [cols]+lines*[range(len(cols))]
#
#    print 'col:{}'.format(len(cols))
#    print 'col_names:{}'.format(len(col_names))
#    print 'lines:{}'.format(lines)
#    print
#
#    print 'itemgetter'
#    t = time.time()
#    tb = select_cols(tb, col_names)
#    t = time.time() - t
#    print t

#    print 'compress'
#    t = time.time()
#    tb = select_cols_2(tb, col_names)
#    t = time.time() - t
#    print t

#    print 'mine'
#    t = time.time()
#    tb = select_cols_3(tb, col_names)
#    t = time.time() - t
#    print t

#    print 'map'
#    t = time.time()
#    tb = select_cols_2(tb, col_names)
#    t = time.time() - t
#    print t





#    tb = [['a','b','c','d'],['1','2','3','4'],['5','6','7','8'],['9','10','11','12']]
#    col_names = ['b', 'a']
#    col_names = []
#    print 'mine'
#    print select_cols_3(tb, col_names)
#    print 'compress'
#    print select_cols_2(tb, col_names)
#    print 'getter'
#    print select_cols(tb, col_names)

#    mon, sec = divmod(t, 60)
#    hr, mon = divmod(mon, 60)
#    print "%d:%02d:%02d" % (hr, mon, sec)


    print 5*'\n'+'ok'
