# -*- coding: utf-8 -*-
"""This module defines classes for parsing the questionnaire from excel format exported by VOXCO"""

from collections import OrderedDict
from xlrd import open_workbook
from csv import reader
from lz4 import frame as lz4_frame
import json
from pyparsing import Word
from pyparsing import operatorPrecedence
from pyparsing import opAssoc
from pyparsing import stringEnd
from pyparsing import printables
import Helper_Functions as hf
from Logics import ParseLogics as plog
import time

ROWS_AFTER_TABLE = 1

class RadioButton():
    
    def __init__(self, qn_chunk, qn_type=None):
        self.qn_chunk = qn_chunk
        self.type = qn_type
        self.name = u''
        self.text = u''
        self.answers_values = []
        self.answers_texts = []
        self.answers = []
        self.variables = []
        self.headers_inds = []
        self.ans_is_vsbl = []
        self.vsbl_inds = []
        self.show_inv = False
        self.data = []
        self.base = None
        self.counts = None
        self.percentages = None
        self.table = u''
        self.repl_vars = None
    
    def replace_vars(self):
        self.variables = [v.replace(u'~', u'' if self.repl_vars == True else u'_') for v in self.variables]
    
    def parse_question(self):
        self.name = hf.select_cols(self.qn_chunk, [u'Name'], lol=False)[1]
        self.text = hf.strip_tags(hf.select_cols(self.qn_chunk, [u'Text'], lol=False)[1])
        mask = [row[0] == u'ANSWER' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        # Parse answers codes: list with codes as unicode strings
        self.answers_values = hf.select_cols(rows, [u'Setting Value'], lol=False)[1:]
        # Parse answers labels: list with labels as unicode strings
        self.answers_texts = hf.select_cols(rows, [u'Text'], lol=False)[1:]
        self.answers_texts = [hf.strip_tags(item) for item in self.answers_texts]
        # Parse question variables: list with variable names as unicode strings
        self.variables = [self.name.upper()]
        self.headers_inds = [i for i,v in enumerate(self.answers_values) if not v]
        if self.type == u'CheckBox':
            # Parse question variables for CheckBox questions: list with variable names as unicode strings
            self.variables = [u'{}{}{}'.format(self.name,u'~C',i).upper() for i in range(1,len(self.answers_values)+1)] if len(self.answers_values) > 1 else [self.name]
            # exclude variables that correspond to headers in CheckBox questions
            self.variables = [var for i,var in enumerate(self.variables) if i not in self.headers_inds]
        self.answers = []
        for v,t in zip(self.answers_values,self.answers_texts):
            self.answers.append((v,t))
        # exclude answers codes that correspond to headers
        self.answers_values = [v for i,v in enumerate(self.answers_values) if i not in self.headers_inds]
        # exclude answers labels that correspond to headers
        self.answers_texts = [v for i,v in enumerate(self.answers_texts) if i not in self.headers_inds]
        # answers: Ordered dict with codes as keys and labels as values, with answers corresponding to headers excluded
        self.answers = OrderedDict([kv for i,kv in enumerate(self.answers) if i not in self.headers_inds])
        mask = [row[0] == u'SETTING' and row[1] == u'Visible' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        self.ans_is_vsbl = hf.select_cols(rows, [u'Setting Value'], lol=False)[1:]
        # exclude answers labels that correspond to headers
        self.ans_is_vsbl = [v for i,v in enumerate(self.ans_is_vsbl) if i not in self.headers_inds]
        # indices if visible answers
        self.vsbl_inds = [i for i,v in enumerate(self.ans_is_vsbl) if v == u'True'] if not self.show_inv else range(len(self.ans_is_vsbl))
    
    def set_data(self, data):
        self.data = hf.select_cols(data, self.variables)
    
    def filter_data(self, fstr):
        '''FORMAT: RadioButton-CheckBox: flt_qn.name:c numbers comma separated or just b-> (b for table base, c for code number)
                                         code1..code2 for range of integer codes both included
                                         Function is called without the flt_qn.name: part'''
        if u'b' in fstr:
            mask = [True if ans else False for ans in hf.select_cols(self.data, self.variables, lol=False)[1:]]
        else:
            codes = hf.open_codes(fstr).split(u',')
            mask = [True if ans in codes else False for ans in hf.select_cols(self.data, self.variables, lol=False)[1:]]
        return mask
    
    def calc_stats(self):
        all_answers = [item[0] for item in self.data[1:]]
        non_missing_answers = [answer for answer in all_answers if answer]
        self.base = len(non_missing_answers)
        self.counts = OrderedDict([(code, hf.toUc(str(non_missing_answers.count(code)))) for code in self.answers_values])
        self.percentages = OrderedDict([(code, u'{0:.2f}'.format(100 * float(self.counts[code]) / float(self.base))) if self.base else (code, u'0') for code in self.answers_values])
    
    def add_logics(self):
        parse_logics = plog(self.qn_chunk)
        logics = parse_logics.question_logics(html=True).strip()
        if logics:
            logics = u'''<a href="#/" class="toggle_this_logs" onclick="toggle_this_func(this);">Hide Question Logics ↑</a> / <a href="#/" class="toggle_all_logs" onclick="toggle_all_func();">Hide All Logics ↑</a><div class="logics">{}</div><br><br>'''.format(logics)
            # logics = u'''<div><a href="#" class="hide" onclick="(function(){{alert(document.getElementsByClassName("logics"););}})();">Hide Logics ↑</a></div><div class="logics">{}</div><br><br>'''.format(logics)
            # logics = u'<label class="drop" for="cb_{}"></label><input id="cb_{}" type="checkbox"><div class="logics">{}</div><br><br>'.format(self.name, self.name, logics)
            # logics = u'<span class="hide" tabindex="0">Hide</span>/<span class="show" tabindex="0">Show</span><br><p class="alert">{}</p>'.format(logics)
            # logics = u'{}<br><br><br>'.format(logics)
        return logics
    
    def html_table(self):
        self.calc_stats()
        html_string = []
        html_string.append(u'<table id="{}" class="rb_cb_table">'.format(self.name))
        html_string.append(u'<tr>')
        html_string.append(u'<th class="header_base" colspan="10">{} /{}/ (Base: <a href="fltr_{}:b" style="color:white;">{}</a>)</th>'.format(self.name, self.type, self.name, self.base))
        html_string.append(u'<th class="header_text" colspan="22">{}</th>'.format(self.text))
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="2">Codes</th>')
        html_string.append(u'<th colspan="22">Labels</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs" colspan="4">Counts</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs" colspan="4">Percentages</th>')
        html_string.append(u'</tr>')
        for i,kv in enumerate(self.answers.iteritems()):
            if i in self.vsbl_inds:
                html_string.append(u'<tr>')
                html_string.append(u'<td colspan="2">{}</td>'.format(kv[0]))
                html_string.append(u'<td class="row_labels" colspan="22">{}</td>'.format(kv[1]))
                html_string.append(u'<td colspan="4"><a href="fltr_{}:{}">{}</a></td>'.format(self.name, kv[0], self.counts[kv[0]]))
                html_string.append(u'<td colspan="4">{}%</td>'.format(self.percentages[kv[0]]))
                html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="2">TOT</th>')
        html_string.append(u'<th colspan="22"></th>')
        cnts = sum(int(cnt) for cnt in self.counts.itervalues())
        html_string.append(u'<th colspan="4">{}</th>'.format(cnts))
        html_string.append(u'<th colspan="4">{0:.0f}%</th>'.format((100 * (float(cnts) / float(self.base))) if self.base else 0.))
        html_string.append(u'</tr>')
        html_string.append(u'</table>'+ROWS_AFTER_TABLE*u'<br>')
        if self.logics:
            html_string.append(self.add_logics())
        self.table = ''.join(html_string)
    
    def __str__(self):
        max_ans_code_len = str((max([len(code) for code in self.answers.keys()])))
#        format_string_1 = '\n'.join([u'{:>'+max_ans_code_len+u'}: {}' for k,v in self.answers.iteritems()])
#        answers = [item for kv in self.answers.iteritems() for item in kv]
#        answers = format_string_1.format(*answers)
        format_string_1 = '\n'.join([u'{:>'+max_ans_code_len+u'}: {}'+u' cnt:{}, prc:{}%' for k,v in self.answers.iteritems()])
        answers = [(item[0][0], item[0][1], item[1], item[2]) for item in zip(self.answers.iteritems(), self.counts.itervalues(), self.percentages.itervalues())]
        answers = [item for ans in answers for item in ans]
        answers = format_string_1.format(*answers)
        variables = ', '.join(self.variables)
        format_string_2 = u'Name: {}\nType: {}\nText: {}\nVariables: {}\nBase: {}\n'+u' Choices '.center(20, u'-')+'\n{}'+('\n'+20*'-')
        report_string = format_string_2.format(self.name, self.type, self.text, variables, self.base, answers)
        return report_string.encode('utf-8')

#########################################################################

class Disposition(RadioButton):
    
    def __init__(self, qn_chunk=None, qn_type=None):
        RadioButton.__init__(self, qn_chunk, qn_type)
    
    def replace_vars(self):
        if self.repl_vars == True:
            self.variables[0] = u'resDisposition'
    
    def parse_question(self):
        self.type = u'Disposition'
        self.name = u'_DISPOSITION_'
        self.text = u'Questionnaire Status'
        self.answers_values = [u'0',u'1',u'2',u'3',u'4',u'5',u'6']
        self.answers_texts = [u'Unused',u'Completed',u'Dropped',u'Screened Out',u'Interrupted',u'Out Of Quota',u'Reset']
        self.answers = OrderedDict([(v,t) for v,t in zip(self.answers_values, self.answers_texts)])
        self.variables = [self.type]
        # indices if visible answers
        self.vsbl_inds = range(len(self.answers))
#########################################################################

class Date(RadioButton):

    def __init__(self, qn_chunk=None, qn_type=None):
        RadioButton.__init__(self, qn_chunk, qn_type)
    
    def parse_question(self):
        self.type = u'Date'
        self.name = u'_DATE_'
        self.text = u'Date of Interview'
        self.variables = [u'LastConnectionDate']
    
    def set_answers(self):
        self.answers_values = sorted([int(dt) for dt in hf.select_cols(self.data, self.variables, lol=False)[1:] if dt])
        self.answers_values = [hf.toUc(str(dt)) for dt in self.answers_values]
        self.answers_texts = [hf.date_str(dt) for dt in self.answers_values]
        self.answers = OrderedDict([(v,t) for v,t in zip(self.answers_values, self.answers_texts)])
        # indices if visible answers
        self.vsbl_inds = range(len(self.answers))
#########################################################################

class DropDownList(RadioButton):
    
    def __init__(self, qn_chunk, qn_type):
        RadioButton.__init__(self, qn_chunk, qn_type)

#########################################################################

class CheckBox(RadioButton):
    
    def __init__(self, qn_chunk, qn_type):
        RadioButton.__init__(self, qn_chunk, qn_type)
    
    def filter_data(self, fstr):
        '''FORMAT: RadioButton-CheckBox: flt_qn.name:c numbers comma separated or just b-> (b for table base, c for code number)
                                         code1..code2 for range of integer codes both included
                                         Function is called without the flt_qn.name: part'''
        if u'b' in fstr:
            mask = [any(ans) for ans in self.data[1:]]
        else:
            codes = hf.open_codes(fstr).split(u',')
            variables = [self.variables[i] for i,v in enumerate(self.answers_values) if v in codes]
            if not variables:
                mask = (len(self.data) - 1) * [False]
            else:
                mask = [any([item == u'1' for item in ans]) for ans in hf.select_cols(self.data, variables)[1:]]
        return mask
    
    def calc_stats(self):
        all_answers = self.data[1:]
        non_missing_answers = [answer for answer in all_answers if any(answer)]
        self.base = len(non_missing_answers)
        self.counts = OrderedDict([])
        for i,code in enumerate(self.answers_values):
            answers = hf.select_cols(self.data, [self.variables[i]], lol=False)[1:]
            _sum = sum(item == u'1' for item in answers)
            self.counts[code] = _sum
        self.percentages = OrderedDict([(code, u'{0:.2f}'.format(100 * float(self.counts[code]) / float(self.base))) if self.base else (code, u'0') for code in self.answers_values])

#########################################################################

class ChoiceGrid(CheckBox):
    
    def __init__(self, qn_chunk, qn_type):
        CheckBox.__init__(self, qn_chunk, qn_type)
        self.qn_chunk = qn_chunk
        self.type = qn_type
        mask = [row[0] == u'COLUMN' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        self.grid_type = hf.select_cols(rows, [u'Type'], lol=False)[1]
        self.rows = None
        self.data = None
        self.mins = None
        self.maxes = None
        self.mean_scores = None
        self.sdvs = None
        self.detr = None
        self.prom = None
        self.detr_cnts = None
        self.neut_cnts = None
        self.prom_cnts = None
    
    def parse_question(self):
        self.name = hf.select_cols(self.qn_chunk, [u'Name'], lol=False)[1]
        self.text = hf.strip_tags(hf.select_cols(self.qn_chunk, [u'Text'], lol=False)[1])
        mask = [row[0] == u'ROW' and row[3] == u'Variable' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        # Parse row texts: list with unicode strings
        rows_texts = hf.select_cols(rows, [u'Text'], lol=False)[1:]
        mask = [row[0] == u'ANSWER' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        # Parse column codes: list with unicode strings
        cols_values = hf.select_cols(rows, [u'Setting Value'], lol=False)[1:]
        # Parse column labels: list with unicode strings
        cols_texts = hf.select_cols(rows, [u'Text'], lol=False)[1:]
        mask = [row[0] == u'VARIABLES' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        rows_names = hf.select_cols(rows, [u'Name'], lol=False)[1:]
        # Parse row variables: list of lists with unicode strings
        rows_variables = [[var] for var in rows_names] if self.grid_type == u'RadioButton' else [[u'{}{}{}'.format(row_name,u'~C',i) if len(cols_values) > 1 else row_name for i in range(1,len(cols_values)+1)] for row_name in rows_names]
        mask = [row[0] == u'SETTING' and row[1] == u'Visible' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        self.ans_is_vsbl = hf.select_cols(rows, [u'Setting Value'], lol=False)[1:]
        # indices if visible columns
        self.vsbl_inds = [i for i,v in enumerate(self.ans_is_vsbl) if v == u'True'] if not self.show_inv else range(len(self.ans_is_vsbl))
        # Rows as RadioButton or CheckBox class instances
        self.rows = [RadioButton(self.qn_chunk, self.grid_type) for i in range(len(rows_texts))] if self.grid_type == u'RadioButton' else [CheckBox(self.qn_chunk, self.grid_type) for i in range(len(rows_texts))]
        self.variables = []
        # set attributes of each row
        for i,row in enumerate(self.rows):
            row.ans_is_vsbl = self.ans_is_vsbl
            row.vsbl_inds = self.vsbl_inds
            row.name = rows_names[i]
            row.text = hf.strip_tags(rows_texts[i])
            row.answers_values = cols_values
            row.answers_texts = [hf.strip_tags(txt) for txt in cols_texts]
            row.variables = rows_variables[i]
            self.variables += row.variables
            row.answers = OrderedDict(zip(row.answers_values,row.answers_texts))
        if self.type == u'NetPromoter':
            mask = [row[0] == u'SETTING' and row[1] == u'Detractors' for row in self.qn_chunk]
            rows = hf.select_rows(self.qn_chunk, mask)
            self.detr = int(hf.select_cols(rows, [u'Setting Value'], lol=False)[1])
            mask = [row[0] == u'SETTING' and row[1] == u'Promoters' for row in self.qn_chunk]
            rows = hf.select_rows(self.qn_chunk, mask)
            self.prom = int(hf.select_cols(rows, [u'Setting Value'], lol=False)[1])
    
    def replace_vars(self):
        if self.grid_type == u'CheckBox':
            self.variables = []
            for i,row in enumerate(self.rows):
                row.repl_vars = self.repl_vars
                row.replace_vars()
                self.variables += row.variables
    
    def set_data(self, data):
        self.data = hf.select_cols(data, self.variables)
        for row in self.rows:
            row.set_data(self.data)
    
    def filter_data(self, fstr):
        '''FORMAT: ChoiceGrid: flt_qn.name:pairs of [r.c] ; separated -> ([b.b] for table base,
                                                                          [r.b] for row base (r>0) and
                                                                          [r.c] for table cell (r,c>0,!=b).
                                                                          c can be of the form c1,c2..c3 like in RadioButton,
                                         where r is the sequential number of the row starting from 1 and c is the code of the row)
                                         Function is called without the flt_qn.name: part'''
        fstr_values = hf.open_codes(fstr).split(u';')
        if u'[b.b]' in fstr_values:
            mask = [any(ans) for ans in self.data[1:]]
        else:
            rows_filter_strings = {int(item.split(u'.')[0][1:]) - 1:u'.'.join(item.split(u'.')[1:])[:-1] for item in fstr_values}
            mask = reduce(lambda x,y:[x1 or y1 for (x1,y1) in zip(x,y)], [self.rows[i].filter_data(s) for i,s in rows_filter_strings.iteritems()])
        return mask
    
    def calc_stats(self):
        all_answers = self.data[1:]
        non_missing_answers = [answer for answer in all_answers if any(answer)]
        self.base = len(non_missing_answers)
        if self.type == u'NetPromoter':
            self.mins, self.maxes, self.mean_scores, self.sdvs, self.detr_cnts, self.neut_cnts, self.prom_cnts = [], [], [], [], [], [], []
        for row in self.rows:
            row.calc_stats()
            if self.type == u'NetPromoter':
                non_miss_answers = [item for item in hf.select_cols(row.data, row.variables, lol=False)[1:] if item]
                mn = [int(ans) for ans in non_miss_answers]
                mn = min(mn) if mn else u'-'
                self.mins.append(mn)
                mx = [int(ans) for ans in non_miss_answers]
                mx = max(mx) if mx else u'-'
                self.maxes.append(mx)
                mean_score = sum([float(ans) for ans in non_miss_answers]) / row.base if non_miss_answers else u'-'
                sdv = (sum([(float(ans) - mean_score) ** 2 for ans in non_miss_answers]) / (row.base - 1)) ** (1/2.) if mean_score != u'-' and row.base > 1 else u'-'
                mean_score = u'{0:.2f}'.format(mean_score) if mean_score != u'-' else mean_score
                self.mean_scores.append(mean_score)
                sdv = u'{0:.2f}'.format(sdv) if sdv != u'-' else sdv
                self.sdvs.append(sdv)
                detr_cnts = len([ans for ans in non_miss_answers if int(ans) <= self.detr])
                self.detr_cnts.append(detr_cnts)
                neut_cnts = len([ans for ans in non_miss_answers if self.detr < int(ans) < self.prom])
                self.neut_cnts.append(neut_cnts)
                prom_cnts = len([ans for ans in non_miss_answers if self.prom <= int(ans)])
                self.prom_cnts.append(prom_cnts)
    
    def html_table(self):
        d = {u'RadioButton':u'S', u'CheckBox':u'M'}
        self.calc_stats()
        first_row = self.rows[0]
        cols_num = len(self.vsbl_inds)
        html_string = []
        html_string.append(u'<table id="{}">'.format(self.name))
        html_string.append(u'<tr>')
        html_string.append(u'<th colspan="3" class="header_base">{} /{} - {}/ (Base:<a href="fltr_{}:[b.b]" style="color:white;">{}</a>)</th>'.format(self.name, self.type, d[self.grid_type], self.name, self.base))
        colspan1 = 2 * (cols_num + 1) + (11 if self.type == u'NetPromoter' else 0)
        html_string.append(u'<th colspan="{}" class="header_text">{}</th>'.format(colspan1, self.text))
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="3">Codes</th>')
        for i,code in enumerate(first_row.answers_values):
            if i in self.vsbl_inds:
                html_string.append(u'<th colspan="2">{}</th>'.format(code))
        colspan2 = 6 if self.type == u'NetPromoter' else 2
        html_string.append(u'<th colspan="{}" rowspan="2">TOTAL</th>'.format(colspan2))
        if self.type == u'NetPromoter':
            html_string.append(u'<th colspan="7">NPS</th>')
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="3">Labels</th>')
        for i,txt in enumerate(first_row.answers_texts):
            if i in self.vsbl_inds:
                html_string.append(u'<th colspan="2">{}</th>'.format(txt))
        if self.type == u'NetPromoter':
            html_string.append(u'<th colspan="2">Detractors [0..{}]</th>'.format(self.detr))
            html_string.append(u'<th colspan="2">Neutrals [{}..{}]</th>'.format(self.detr + 1, self.prom - 1))
            html_string.append(u'<th colspan="2">Promoters [{}..{}]</th>'.format(self.prom, first_row.answers_values[-1]))
            html_string.append(u'<th rowspan="2">&nbsp;NPScore&nbsp;</th>')
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th>Row</th><th>Text</th><th>Bases</th>')
        for i in range(cols_num + 1):
            html_string.append(u'<th>Counts</th><th>Percentages</th>')
        if self.type == u'NetPromoter':
            html_string.append(u'<th>MIN</th>')
            html_string.append(u'<th>MAX</th>')
            html_string.append(u'<th>MS</th>')
            html_string.append(u'<th>SDV</th>')
            for i in range(3):
                html_string.append(u'<th>Counts</th><th>Percentages</th>')
        html_string.append(u'</tr>')
        for i,row in enumerate(self.rows):
            html_string.append(u'<tr>')
            html_string.append(u'<td>{}</td>'.format(i+1))
            html_string.append(u'<td class="row_labels">{}</td>'.format(row.text))
            html_string.append(u'<td class="base_tot_cell"><a href="fltr_{}:[{}.b]">{}</a></td>'.format(self.name, i + 1, row.base))
            for j,code in enumerate(row.answers_values):
                if j in self.vsbl_inds:
                    html_string.append(u'<td><a href="fltr_{}:[{}.{}]">{}</a></td>'.format(self.name, i + 1, code, row.counts[code]))
                    html_string.append(u'<td>{}%</td>'.format(row.percentages[code]))
                    cnts = sum(int(cnt) for cnt in row.counts.itervalues())
            html_string.append(u'<td class="base_tot_cell">{}</td>'.format(cnts))
            html_string.append(u'<td class="base_tot_cell">{0:.0f}%</td>'.format((100 * (float(cnts) / float(row.base))) if row.base else 0.))
            if self.type == u'NetPromoter':
                html_string.append(u'<td>{}</td>'.format(self.mins[i]))
                html_string.append(u'<td>{}</td>'.format(self.maxes[i]))
                html_string.append(u'<td>{}</td>'.format(self.mean_scores[i]))
                html_string.append(u'<td>{}</td>'.format(self.sdvs[i]))
                html_string.append(u'<td>{}</td>'.format(self.detr_cnts[i]))
                prcd = 100 * self.detr_cnts[i] / float(row.base) if row.base != 0 else 0.
                html_string.append(u'<td>{0:.2f}%</td>'.format(prcd))
                html_string.append(u'<td>{}</td>'.format(self.neut_cnts[i]))
                prc = 100 * self.neut_cnts[i] / float(row.base) if row.base != 0 else 0.
                html_string.append(u'<td>{0:.2f}%</td>'.format(prc))
                html_string.append(u'<td>{}</td>'.format(self.prom_cnts[i]))
                prcp = 100 * self.prom_cnts[i] / float(row.base) if row.base != 0 else 0.
                html_string.append(u'<td>{0:.2f}%</td>'.format(prcp))
                prc = prcp - prcd
                html_string.append(u'<td style="color:{};">{:.2f}%</td>'.format(u'black' if prc >= 0 else u'red', prc))
            html_string.append(u'</tr>')
        html_string.append(u'</table>'+ROWS_AFTER_TABLE*u'<br>')
        if self.logics:
            html_string.append(self.add_logics())        
        self.table = ''.join(html_string)
    
    def __str__(self):
        format_string = u'Name: {}\nType: {}\nText: {}\nBase: {}\n'+u' ROWS '.center(20, u'-')+'\n'
        format_string += '\n'.join([hf.toUc(row.__str__()) for row in self.rows])
        report_string = format_string.format(self.name, self.type, self.text, self.base)
        return report_string.encode('utf-8')

#########################################################################

class NetPromoter(ChoiceGrid):
    
    def __init__(self, qn_chunk, qn_type):
        ChoiceGrid.__init__(self, qn_chunk, qn_type)

#########################################################################

class NumericAnswer(RadioButton):
    
    def __init__(self, qn_chunk, qn_type):
        RadioButton.__init__(self, qn_chunk, qn_type)
        self.num_ans_counts = None
        self.num_ans_prc = None
        self.min = None
        self.max = None
        self.mean_score = None
        self.sdv = None
    
    def filter_data(self, fstr):
        '''FORMAT: NumericAnswer: flt_qn.name:r real numbers comma separated or just b for table base
                                             r can also be a code of the choice answers, numeric or not but not "b" as this is for base
                                             r1..r2 for range of real numbers both included
                                         Function is called without the flt_qn.name: part'''
        if fstr == u'b':
            mask = [True if ans else False for ans in hf.select_cols(self.data, self.variables, lol=False)[1:]]
        else:
            codes = hf.open_codes(fstr, real=True)
            mask = []
            for ans in hf.select_cols(self.data, self.variables, lol=False)[1:]:
                if not ans:
                    mask.append(False)
                else:
                    try:
                        new_ans = float(ans)
                        mask.append(any([new_ans == item if not isinstance(item, list) else item[0] <= new_ans <= item[1] for item in codes]))
                    except:
                        mask.append(any([ans == item if not isinstance(item, list) else False for item in codes]))
        return mask
    
    def calc_stats(self):
        all_answers = [item[0] for item in self.data[1:]]
        non_missing_answers = [answer for answer in all_answers if answer]
        self.base = len(non_missing_answers)
        self.counts = OrderedDict([(code, hf.toUc(str(non_missing_answers.count(code)))) for code in self.answers_values])
        self.percentages = OrderedDict([(code, u'{0:.2f}'.format(100 * float(self.counts[code]) / float(self.base))) if self.base else (code, u'0') for code in self.answers_values])
        num_ans = [ans for ans in non_missing_answers if ans not in self.answers_values]
        self.num_ans_counts = len(num_ans)
        self.num_ans_prc = u'{0:.2f}'.format(100 * float(self.num_ans_counts) / float(self.base)) if self.base else u'0'
        self.mean_score = sum([float(ans) for ans in num_ans]) / float(self.num_ans_counts) if num_ans else u'-'
        self.sdv = (sum([(float(ans) - self.mean_score) ** 2 for ans in num_ans]) / float(self.num_ans_counts - 1)) ** (1/2.) if self.num_ans_counts > 1 else u'-'
        self.mean_score = u'{0:.2f}'.format(self.mean_score) if self.mean_score != u'-' else self.mean_score
        self.sdv = u'{0:.2f}'.format(self.sdv) if self.sdv != u'-' else self.sdv
        self.min = u'{0:.2f}'.format(min([float(ans) for ans in num_ans])) if num_ans else u'-'
        self.max = u'{0:.2f}'.format(max([float(ans) for ans in num_ans])) if num_ans else u'-'
    
    def html_table(self):
        self.calc_stats()
        html_string = []
        html_string.append(u'<table id="{}">'.format(self.name))
        html_string.append(u'<tr>')
        html_string.append(u'<th colspan="2" class="header_base">{} /{}/ (Base:<a href="fltr_{}:b" style="color:white;">{}</a>)</th>'.format(self.name, self.type, self.name, self.base))
        html_string.append(u'<th colspan="6" class="header_text">{}</th>'.format(self.text))
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th>Codes</th>')
        html_string.append(u'<th>Labels</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">Counts</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">Percentages</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">MIN</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">MAX</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">MS</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">SDV</th>')
        html_string.append(u'</tr>')
        html_string.append(u'<tr>')
        html_string.append(u'<td>{}</td>'.format(u'-'))
        html_string.append(u'<td class="row_labels"><b>Numeric Answers</b></td>')
        fltr_exp = u'{}:b&~{}:{}'.format(self.name, self.name, u','.join([ans for ans in self.answers_values]))
        html_string.append(u'<td><a href="fltr_{}">{}</a></td>'.format(fltr_exp, self.num_ans_counts))
        html_string.append(u'<td>{}%</td>'.format(self.num_ans_prc))
        html_string.append(u'<td>{}</td>'.format(self.min))
        html_string.append(u'<td>{}</td>'.format(self.max))
        html_string.append(u'<td>{}</td>'.format(self.mean_score))
        html_string.append(u'<td>{}</td>'.format(self.sdv))
        html_string.append(u'</tr>')
        for i,kv in enumerate(self.answers.iteritems()):
            if i in self.vsbl_inds:
                html_string.append(u'<tr>')
                html_string.append(u'<td>{}</td>'.format(kv[0]))
                html_string.append(u'<td class="row_labels">{}</td>'.format(kv[1]))
                html_string.append(u'<td><a href="fltr_{}:{}">{}</a></td>'.format(self.name, kv[0], self.counts[kv[0]]))
                html_string.append(u'<td>{}%</td>'.format(self.percentages[kv[0]]))
                if i == 0:
                    rowspan = len(self.vsbl_inds) + 1
                    html_string.append(u'<td class="header_rest" colspan="4" rowspan="{}"></td>'.format(rowspan))
                html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th>TOT</th>')
        html_string.append(u'<th></th>')
        cnts = sum(int(cnt) for cnt in self.counts.itervalues()) + self.num_ans_counts
        html_string.append(u'<th>{}</th>'.format(cnts))
        html_string.append(u'<th>{0:.0f}%</th>'.format((100 * (float(cnts) / float(self.base))) if self.base else 0.))
        if not self.vsbl_inds:
            html_string.append(u'<td class="header_rest" colspan="4"></td>')
        html_string.append(u'</tr>')
        html_string.append(u'</table>'+ROWS_AFTER_TABLE*u'<br>')
        if self.logics:
            html_string.append(self.add_logics())        
        self.table = ''.join(html_string)

#########################################################################

class CASEID(NumericAnswer):
    
    def __init__(self, qn_chunk=None, qn_type=None):
        NumericAnswer.__init__(self, qn_chunk, qn_type)
    
    def replace_vars(self):
        if self.repl_vars == True:
            self.variables[0] = u'CaseId'
    
    def parse_question(self):
        self.text = u"Questionnaire's unique Id"
        self.type = u'CASEID'
        self.name = u'_CASEID_'
        self.variables = [u'CaseID']
    
    def html_table(self):
        self.table = ''

#########################################################################

class Slider(NumericAnswer):
    
    def __init__(self, qn_chunk, qn_type):
        NumericAnswer.__init__(self, qn_chunk, qn_type)
    
    def html_table(self):
        self.calc_stats()
        html_string = []
        html_string.append(u'<table id="{}">'.format(self.name))
        html_string.append(u'<tr>')
        html_string.append(u'<th class="header_base">{} /{}/ (Base:<a href="fltr_{}:b" style="color:white;">{}</a>)</th>'.format(self.name, self.type, self.name, self.base))
        html_string.append(u'<th colspan="4" class="header_text">{}</th>'.format(self.text))
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th class="header_rest" rowspan="2"></td>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">MIN</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">MAX</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">MS</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">SDV</th>')
        html_string.append(u'</tr>')
        html_string.append(u'<tr>')
        html_string.append(u'<td>{}</td>'.format(self.min))
        html_string.append(u'<td>{}</td>'.format(self.max))
        html_string.append(u'<td>{}</td>'.format(self.mean_score))
        html_string.append(u'<td>{}</td>'.format(self.sdv))
        html_string.append(u'</tr>')
        html_string.append(u'</table>'+ROWS_AFTER_TABLE*u'<br>')
        if self.logics:
            html_string.append(self.add_logics())
        self.table = ''.join(html_string)

#########################################################################

class DURATION(Slider):
    
    def __init__(self, qn_chunk=None, qn_type=None):
        NumericAnswer.__init__(self, qn_chunk, qn_type)
    
    def replace_vars(self):
        if self.repl_vars == True:
            self.variables[0] = u'ConnectionDurationInSeconds'
    
    def parse_question(self):
        self.type = u'Duration'
        self.name = u'_DURATION_'
        self.text = u'Duration of Interview'
        self.variables = [u'Durationofconnectioninseconds']
    
    def calc_stats(self):
        all_answers = [item[0] for item in self.data[1:]]
        non_missing_answers = [answer for answer in all_answers if answer]
        self.base = len(non_missing_answers)
        self.counts = OrderedDict([(code, hf.toUc(str(non_missing_answers.count(code)))) for code in self.answers_values])
        self.percentages = OrderedDict([(code, u'{0:.2f}'.format(100 * float(self.counts[code]) / float(self.base))) if self.base else (code, u'0') for code in self.answers_values])
        num_ans = [ans for ans in non_missing_answers if ans not in self.answers_values]
        self.num_ans_counts = len(num_ans)
        self.num_ans_prc = u'{0:.2f}'.format(100 * float(self.num_ans_counts) / float(self.base)) if self.base else u'0'
        self.mean_score = sum([float(ans) for ans in num_ans]) / float(self.num_ans_counts) if num_ans else u'-'
        self.sdv = (sum([(float(ans) - self.mean_score) ** 2 for ans in num_ans]) / float(self.num_ans_counts - 1)) ** (1/2.) if self.num_ans_counts > 1 else u'-'
        self.mean_score = u'{}'.format(hf.display_time(int(self.mean_score))) if self.mean_score != u'-' else self.mean_score
        self.sdv = u'{0:.2f}'.format(self.sdv) if self.sdv != u'-' else self.sdv
        self.min = u'{}'.format(hf.display_time(int(min([float(ans) for ans in num_ans])))) if num_ans else u'-'
        self.max = u'{}'.format(hf.display_time(int(max([float(ans) for ans in num_ans])))) if num_ans else u'-'

#########################################################################

class RunningTotal(NumericAnswer):
    
    def __init__(self, qn_chunk, qn_type):
        NumericAnswer.__init__(self, qn_chunk, qn_type)
        self.rows = []
        self.rows_variables = []
        self.cols_variables = []
        self.rowbases = []
        self.colbases = []
    
    def parse_question(self):
        self.name = hf.select_cols(self.qn_chunk, [u'Name'], lol=False)[1]
        self.text = hf.strip_tags(hf.select_cols(self.qn_chunk, [u'Text'], lol=False)[1])
        mask = [row[0] == u'ROW' and row[3] == u'Variable' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        rows_texts = hf.select_cols(rows, [u'Text'], lol=False)[1:]
        mask = [row[0] == u'SETTING' and u'Labels_' in row[1] for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        cols_texts = hf.select_cols(rows, [u'Setting Value'], lol=False)[1:]
        mask = [row[0] == u'VARIABLES' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        self.rows_variables = hf.select_cols(rows, [u'Name'], lol=False)[1:]
        self.rows_variables = [u''.join(item.split()).upper().split(u',') for item in self.rows_variables]
        if not cols_texts:cols_texts = len(self.rows_variables[0]) * [u'']
        self.rows = [[NumericAnswer(self.qn_chunk, u'NumericAnswer') for j in range(len(self.rows_variables[0]))] for i in range(len(rows_texts))]
        self.cols_variables = zip(*self.rows_variables)
        self.variables = [var for subl in self.rows_variables for var in subl]
        for i,r in enumerate(self.rows):
            for j,qn in enumerate(r):
                qn.variables = [self.rows_variables[i][j]]
                qn.text = rows_texts[i]
                qn.answers_texts = cols_texts[j]
                qn.answers_values = []
    
    def set_data(self, data):
        self.data = hf.select_cols(data, self.variables)
        for i,r in enumerate(self.rows):
            for j,qn in enumerate(r):
                qn.set_data(self.data)
    
    def mask_func(self, fstr):
        if fstr == u'[b.b]':
            mask = [any(ans) for ans in self.data[1:]]
        elif fstr.startswith(u'[b.'):
            col_ind = int(fstr.split(u'.')[-1][:-1]) - 1
            mask = [any(line) for line in hf.select_cols(self.data, self.cols_variables[col_ind])[1:]]
        elif fstr.endswith(u'.b]') and u':' not in fstr:
            row_ind = int(fstr.split(u'.')[0][1:]) - 1
            mask = [any(line) for line in hf.select_cols(self.data, self.rows_variables[row_ind])[1:]]
        elif u':' in fstr:
            r_c, exp = fstr[1:-1].split(u':')
            r, c = r_c.split(u'.')
            r = int(r) - 1
            c = int(c) - 1
            mask = self.rows[r][c].filter_data(exp)
        return mask
    
    def filter_data(self, fstr):
        '''FORMAT: RunningTotal: flt_qn.name:pairs of [r.c] ; separated-> ([b.b] for table base,
                                                               [r.b] for row base (r>0)
                                                               [b.c] for col base (c>0) and
                                                               [r.c:exp] for table  cell (r,c) numeric condition with exp as in Numeric class
                                         where r is the sequential number of the row starting from 1 and c is the code of the row)
                                         Function is called without the flt_qn.name: part'''

        fstr_values = fstr.split(u';')
        mask = reduce(lambda x,y:[x1 or y1 for (x1,y1) in zip(x,y)], [self.mask_func(item) for item in fstr_values])
        return mask
    
    def calc_stats(self):
        all_answers = self.data[1:]
        non_missing_answers = [answer for answer in all_answers if any(answer)]
        self.base = len(non_missing_answers)
        self.rowbases = [sum(any(line) for line in hf.select_cols(self.data, [qn.variables[0] for qn in r])[1:]) for r in self.rows] if self.base != 0 else len(self.rows)*[0]
        self.colbases = [sum(any(line) for line in hf.select_cols(self.data, [row[i].variables[0] for row in self.rows])[1:]) for i in range(len(self.rows[0]))] if self.base != 0 else len(self.rows[0])*[0]
        for i,r in enumerate(self.rows):
            for j,qn in enumerate(r):
                qn.calc_stats()
    
    def html_table(self):
        self.calc_stats()
        first_row = self.rows[0]
        cols_num = len(first_row)
        html_string = []
        html_string.append(u'<table id="{}">'.format(self.name))
        html_string.append(u'<tr>')
        html_string.append(u'<th colspan="3" class="header_base">{} /{}/ (Base:<a href="fltr_{}:[b.b]" style="color:white;">{}</a>)</th>'.format(self.name, self.type, self.name, self.base))
        html_string.append(u'<th colspan="{}" class="header_text">{}</th>'.format(5 * cols_num + 1, self.text))
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="3">Columns</th>')
        for i,qn in enumerate(first_row):
            html_string.append(u'<th colspan="5">{}</th>'.format(qn.answers_texts))
        html_string.append(u'<th colspan="1" rowspan="2">TOTAL</th>')
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="3">Bases</th>')
        for i,b in enumerate(self.colbases):
            html_string.append(u'<th colspan="5"><a href="fltr_{}:[b.{}]">{}</a></th>'.format(self.name, i + 1, b))
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th>Row</th><th>Text</th><th>Bases</th>')
        for i in range(cols_num):
            html_string.append(u'<th>Counts</th><th>MIN</th><th>MAX</th><th>MS</th><th>SDV</th>')
        html_string.append(u'<th>Counts</th>')
        html_string.append(u'</tr>')
        for i,row in enumerate(self.rows):
            html_string.append(u'<tr>')
            html_string.append(u'<td>{}</td>'.format(i+1))
            html_string.append(u'<td class="row_labels">{}</td>'.format(row[0].text))
            html_string.append(u'<td class="base_tot_cell"><a href="fltr_{}:[{}.b]">{}</a></td>'.format(self.name, i + 1, self.rowbases[i]))
            for j,qn in enumerate(row):
                html_string.append(u'<td><a href="fltr_{}:[{}.{}:b]">{}</a></td>'.format(self.name, i + 1, j + 1, qn.num_ans_counts))
                html_string.append(u'<td>{}</td>'.format(qn.min))
                html_string.append(u'<td>{}</td>'.format(qn.max))
                html_string.append(u'<td>{}</td>'.format(qn.mean_score))
                html_string.append(u'<td>{}</td>'.format(qn.sdv))
            cnts = sum([qn.num_ans_counts for qn in row])
            html_string.append(u'<td class="base_tot_cell">{}</td>'.format(cnts))
            html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="3">TOT</th>')
        cnts = []
        for i in range(cols_num):
            cnts1 = sum([qn.num_ans_counts for qn in [r[i] for r in self.rows]])
            cnts.append(cnts1)
            html_string.append(u'<th colspan="5">{}</th>'.format(cnts1))
        html_string.append(u'<th>{}</th>'.format(sum(cnts)))
        html_string.append(u'</tr>')
        html_string.append(u'</table>'+ROWS_AFTER_TABLE*u'<br>')
        if self.logics:
            html_string.append(self.add_logics())        
        self.table = ''.join(html_string)

#########################################################################

class NumericRanking(RadioButton):
    
    def __init__(self, qn_chunk, qn_type):
        RadioButton.__init__(self, qn_chunk, qn_type)
        self.max_allowed_ans = None
        self.vsbl_inds = None
        self.row_bases = None
        self.row_prcnts = None
        self.row_mins = None
        self.row_maxes = None
        self.row_mean_scores = None
        self.row_sdvs = None
        self.cols = None
    
    def parse_question(self):
        self.name = hf.select_cols(self.qn_chunk, [u'Name'], lol=False)[1]
        self.text = hf.strip_tags(hf.select_cols(self.qn_chunk, [u'Text'], lol=False)[1])
        if any(u'MaxAllowedAnswers' in lst for lst in self.qn_chunk):
            mask = [row[0] == u'SETTING' and row[1] == u'MaxAllowedAnswers' for row in self.qn_chunk]
            rows = hf.select_rows(self.qn_chunk, mask)
            self.max_allowed_ans = int(hf.select_cols(rows, [u'Setting Value'], lol=False)[1])
        mask = [row[0] == u'ANSWER' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        row_texts = hf.select_cols(rows, [u'Text'], lol=False)[1:]
        row_codes = hf.select_cols(rows, [u'Setting Value'], lol=False)[1:]
        mask = [row[0] == u'SETTING' and row[1] == u'Visible' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        row_is_vsbl = hf.select_cols(rows, [u'Setting Value'], lol=False)[1:]
        self.vsbl_inds = [i for i,v in enumerate(row_is_vsbl) if v == u'True'] if not self.show_inv else range(len(row_is_vsbl))
        self.variables = [u'{}{}{}'.format(self.name, u'~M', i).upper() for i in (range(1, self.max_allowed_ans + 1) if self.max_allowed_ans is not None else range(1, len(row_texts) + 1))] if not (self.max_allowed_ans == 1 or (self.max_allowed_ans is None and len(row_texts) == 1)) else [self.name]
        self.cols = [RadioButton(self.qn_chunk) for i in range(len(self.variables))]
        for i,col in enumerate(self.cols):
            col.name = self.name
            col.text = u'Rank: {}'.format(i + 1)
            col.answers_texts = row_texts
            col.answers_values = row_codes
            col.answers = OrderedDict(zip(col.answers_values, col.answers_texts))
            col.variables = [self.variables[i]]
    
    def replace_vars(self):
        for col in self.cols:
            col.repl_vars = self.repl_vars
            col.replace_vars()
        self.variables = [v.replace(u'~', u'' if self.repl_vars == True else u'_') for v in self.variables]
    
    def set_data(self, data):
        self.data = hf.select_cols(data, self.variables)
        for col in self.cols:
            col.set_data(self.data)
    
    def mask_func(self, fstr):
        if u'[b.b]' in fstr:
            mask = [any(ans) for ans in self.data[1:]]
        elif fstr.endswith(u'.b]'):
            code = fstr.split(u'.')[0][1:]
            mask = [any(ans == code for ans in line) for line in hf.select_cols(self.data, self.variables)[1:]]
        elif fstr.startswith(u'[b.'):
            col_ind = int(fstr.split(u'.')[-1][:-1]) - 1
            mask = [True if ans else False for ans in hf.select_cols(self.data, [self.variables[col_ind]], lol=False)[1:]]
        else:
            code, col_ind = fstr[1:-1].split(u'.')
            col_ind = int(col_ind) - 1
            mask = [ans == code for ans in hf.select_cols(self.data, [self.variables[col_ind]], lol=False)[1:]]
        return mask
    
    def filter_data(self, fstr):
        '''FORMAT: NumericRanking: flt_qn.name:pairs of [r.c] ; separated-> ([b.b] for table base,
                                                               [r.b] for row base (r>0)
                                                               [b.c] for col base (c>0) and
                                                               [r.c] for table cell base (r,c>0,!=b)
                                         where r is the row code c is the rank (1,2,3 etc))
                                         Function is called without the flt_qn.name: part'''
        fstr_values = fstr.split(u';')
        mask = reduce(lambda x,y:[x1 or y1 for (x1,y1) in zip(x,y)], [self.mask_func(item) for item in fstr_values])
        return mask
    
    def calc_stats(self):
        all_answers = self.data[1:]
        non_missing_answers = [answer for answer in all_answers if any(answer)]
        self.base = len(non_missing_answers)
        for col in self.cols:
            col.calc_stats()
            col.percentages = OrderedDict([(code, u'{0:.2f}'.format(100 * float(col.counts[code]) / float(self.base))) if self.base else (code, u'0') for code in col.answers_values])
        self.row_bases, self.row_prcnts, self.row_mins, self.row_maxes, self.row_mean_scores, self.row_sdvs = [], [], [], [], [], []
        for i,code in enumerate(self.cols[0].answers_values):
            row_base = sum([any([item == code for item in line]) for line in self.data[1:]])
            self.row_bases.append(row_base)
            row_prcnt = 100 * row_base / float(self.base) if self.base !=0 else 0.
            self.row_prcnts.append(row_prcnt)
            min_max = [any(ans == code for ans in hf.select_cols(self.data, [vrbl], lol=False)[1:]) for vrbl in self.variables]
            min_max = [i + 1 for i,v in enumerate(min_max) if v == True]
            mn = min(min_max) if min_max else u'-'
            self.row_mins.append(mn)
            mx = max(min_max) if min_max else u'-'
            self.row_maxes.append(mx)
            mean_score = sum([float(line.index(code) + 1 if code in line else len(self.variables) + 1) for line in hf.select_cols(self.data, self.variables)[1:] if any(line)])
            mean_score = mean_score / self.base if self.row_bases[-1] != 0 else u'-'
            sdv = (sum([(float(line.index(code) + 1 if code in line else len(self.variables) + 1) - mean_score) ** 2 for line in hf.select_cols(self.data, self.variables)[1:] if any(line)]) / (self.base - 1)) ** (1/2.) if mean_score != u'-' and self.base > 1 else u'-'
            mean_score = u'{0:.2f}'.format(mean_score) if mean_score != u'-' else mean_score
            self.row_mean_scores.append(mean_score)
            sdv = u'{0:.2f}'.format(sdv) if sdv != u'-' else sdv
            self.row_sdvs.append(sdv)
    
    def html_table(self):
        self.calc_stats()
        cols_num = len(self.cols)
        html_string = []
        html_string.append(u'<table id="{}">'.format(self.name))
        html_string.append(u'<tr>')
        html_string.append(u'<th colspan="3" class="header_base">{} /{}/ (Base:<a href="fltr_{}:[b.b]" style="color:white;">{}</a>)</th>'.format(self.name, self.type, self.name, self.base))
        html_string.append(u'<th colspan="{}" class="header_text">{}</th>'.format(2 * cols_num + 5, self.text))
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="3">Rankings</th>')
        for i in range(cols_num):
            html_string.append(u'<th colspan="2">Rank: {}</th>'.format(i + 1))
        html_string.append(u'<th colspan="5" rowspan="2">TOTAL</th>')
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="3">Bases</th>')
        for i,col in enumerate(self.cols):
            html_string.append(u'<th colspan="2"><a href="fltr_{}:[b.{}]">{}</a></th>'.format(col.name, i + 1, col.base))
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th>Codes</th><th>Text</th><th>Bases</th>')
        for i in range(cols_num):
            html_string.append(u'<th>Counts</th><th>Percentages</th>')
        html_string.append(u'<th>Percentages</th><th>MIN</th><th>MAX</th><th>MS</th><th>SDV</th>')
        html_string.append(u'</tr>')
        for i,kv in enumerate(self.cols[0].answers.iteritems()):
            if i in self.vsbl_inds:
                html_string.append(u'<tr>')
                html_string.append(u'<td>{}</td>'.format(kv[0]))
                html_string.append(u'<td class="row_labels">{}</td>'.format(kv[1]))
                html_string.append(u'<td class="base_tot_cell"><a href="fltr_{}:[{}.b]">{}</a></td>'.format(self.name, i + 1, self.row_bases[i]))
                for j,col in enumerate(self.cols):
                    html_string.append(u'<td><a href="fltr_{}:[{}.{}]">{}</a></td>'.format(self.name, i + 1, j + 1, col.counts[kv[0]]))
                    html_string.append(u'<td>{}%</td>'.format(col.percentages[kv[0]]))
                html_string.append(u'<td class="base_tot_cell">{0:.0f}%</td>'.format(self.row_prcnts[i]))
                html_string.append(u'<td class="base_tot_cell">{}</td>'.format(self.row_mins[i]))
                html_string.append(u'<td class="base_tot_cell">{}</td>'.format(self.row_maxes[i]))
                html_string.append(u'<td class="base_tot_cell">{}</td>'.format(self.row_mean_scores[i]))
                html_string.append(u'<td class="base_tot_cell">{}</td>'.format(self.row_sdvs[i]))
                html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="3">TOT</th>')
        for i,col in enumerate(self.cols):
            cnts = sum([int(item) for item in col.counts.itervalues()])
            html_string.append(u'<th>{}</th>'.format(cnts))
            prcnts = 100 * float(cnts) / self.base if self.base != 0 else 0.
            html_string.append(u'<th>{0:.0f}%</th>'.format(prcnts))
        html_string.append(u'<th colspan="5"></th>')
        html_string.append(u'</tr>')
        html_string.append(u'</table>'+ROWS_AFTER_TABLE*u'<br>')
        if self.logics:
            html_string.append(self.add_logics())        
        self.table = ''.join(html_string)

#########################################################################

class DragDropRanking(NumericRanking):
    
    def __init__(self, qn_chunk, qn_type):
        NumericRanking.__init__(self, qn_chunk, qn_type)

#########################################################################

class TextAnswer(RadioButton):
    
    def __init__(self, qn_chunk, qn_type):
        RadioButton.__init__(self, qn_chunk, qn_type)
        self.txt_ans_counts = None
        self.txt_ans_prc = None
    
    def filter_data(self, fstr):
        '''FORMAT: TextAnswer: flt_qn.name:b for table base or r (!=b) for the code of the choice answers.
                                           Function is called without the flt_qn.name: part'''
        if fstr == u'b':
            mask = [True if ans else False for ans in hf.select_cols(self.data, self.variables, lol=False)[1:]]
        else:
            codes = fstr.split(u',')
            mask = [True if ans in codes else False for ans in hf.select_cols(self.data, self.variables, lol=False)[1:]]
        return mask
    
    def calc_stats(self):
        all_answers = [item[0] for item in self.data[1:]]
        non_missing_answers = [answer for answer in all_answers if answer]
        self.base = len(non_missing_answers)
        self.counts = OrderedDict([(code, hf.toUc(str(non_missing_answers.count(code)))) for code in self.answers_values])
        self.percentages = OrderedDict([(code, u'{0:.2f}'.format(100 * float(self.counts[code]) / float(self.base))) if self.base else (code, u'0') for code in self.answers_values])
        txt_ans = [ans for ans in hf.select_cols(self.data, self.variables, lol=False)[1:] if ans and ans not in self.answers_values]
        self.txt_ans_counts = len(txt_ans)
        self.txt_ans_prc = u'{0:.2f}'.format(100 * float(self.txt_ans_counts) / float(self.base)) if self.base else u'0'
    
    def html_table(self):
        self.calc_stats()
        html_string = []
        html_string.append(u'<table id="{}">'.format(self.name))
        html_string.append(u'<tr>')
        html_string.append(u'<th colspan="2" class="header_base">{} /{}/ (Base:<a href="fltr_{}:b" style="color:white;">{}</a>)</th>'.format(self.name, self.type, self.name, self.base))
        html_string.append(u'<th colspan="2" class="header_text">{}</th>'.format(self.text))
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th>Codes</th>')
        html_string.append(u'<th>Labels</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">Counts</th>')
        html_string.append(u'<th class="rb_cb_cnts_prcs">Percentages</th>')
        html_string.append(u'</tr>')
        html_string.append(u'<tr>')
        html_string.append(u'<td>{}</td>'.format(u'-'))
        html_string.append(u'<td class="row_labels"><b>Text Answers</b></td>')
        fltr_exp = u'{}:b&~{}:{}'.format(self.name, self.name, u','.join([ans for ans in self.answers_values]))
        html_string.append(u'<td><a href="fltr_{}">{}</a></td>'.format(fltr_exp, self.txt_ans_counts))
        html_string.append(u'<td>{}%</td>'.format(self.txt_ans_prc))
        html_string.append(u'</tr>')
        for i,kv in enumerate(self.answers.iteritems()):
            if i in self.vsbl_inds:
                html_string.append(u'<tr>')
                html_string.append(u'<td>{}</td>'.format(kv[0]))
                html_string.append(u'<td class="row_labels">{}</td>'.format(kv[1]))
                html_string.append(u'<td><a href="fltr_{}:{}">{}</a></td>'.format(self.name, kv[0], self.counts[kv[0]]))
                html_string.append(u'<td>{}%</td>'.format(self.percentages[kv[0]]))
                html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th>TOT</th>')
        html_string.append(u'<th></th>')
        cnts = sum(int(cnt) for cnt in self.counts.itervalues()) + self.txt_ans_counts
        html_string.append(u'<th>{}</th>'.format(cnts))
        html_string.append(u'<th>{0:.0f}%</th>'.format((100 * (float(cnts) / float(self.base))) if self.base else 0.))
        html_string.append(u'</tr>')
        html_string.append(u'</table>'+ROWS_AFTER_TABLE*u'<br>')
        if self.logics:
            html_string.append(self.add_logics())        
        self.table = ''.join(html_string)

#########################################################################

class HybridGrid(RunningTotal):
    
    def __init__(self, qn_chunk, qn_type):
        RunningTotal.__init__(self, qn_chunk, qn_type)
        self.qn_chunk = qn_chunk
        self.type = qn_type
        self.col_chunks = []
        self.col_types = []
        self.rows_texts = []
        self.cols_texts = []
        self.cols_names = []
        self.row_bases = []
        self.row_cnts = []
        self.row_prcnts = []
        self.in_row_cnts = []
        self.in_row_prcnts = []
    
    def parse_question(self):
        self.name = hf.select_cols(self.qn_chunk, [u'Name'], lol=False)[1]
        self.text = hf.strip_tags(hf.select_cols(self.qn_chunk, [u'Text'], lol=False)[1])
        mask = [row[0] == u'ROW' and row[3] == u'Variable' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        self.rows_texts = hf.select_cols(rows, [u'Text'], lol=False)[1:]

        mask = [row[0] == u'VARIABLES' for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        rows_variables = hf.select_cols(rows, [u'Name'], lol=False)[1:]
        rows_variables = [u''.join(item.split()).upper().split(u',') for item in rows_variables]

        mask = [row[0] == u'SETTING' and u'Labels_' in row[1] for row in self.qn_chunk]
        rows = hf.select_rows(self.qn_chunk, mask)
        self.cols_texts = []
        cols_lbls = hf.select_cols(rows, [u'Name'], lol=False)[1:]
        for i in range(len(rows_variables[0])):
            lbl = u'Labels_{}'.format(i+1)
            if lbl in cols_lbls:
                mask = [row[0] == u'SETTING' and lbl in row[1] for row in self.qn_chunk]
                rows = hf.select_rows(self.qn_chunk, mask)
                self.cols_texts.append(' - '.join(hf.select_cols(rows, [u'Setting Value'], lol=False)[1:]))
            else:
                self.cols_texts.append(u'')

        inds = [ind for ind,row in enumerate(self.qn_chunk) if row[0] == u'COLUMN']
        self.col_chunks = [[self.qn_chunk[0]]+chunk for chunk in hf.split_to_chunks(self.qn_chunk, inds)[1:]]
        self.col_types = [hf.select_cols(col_chunk, [u'Type'], lol=False)[1] for col_chunk in self.col_chunks]
        self.col_types = [ctype.replace(u'Text', u'TextAnswer') for ctype in self.col_types]
        self.rows = [[eval(col_type)(self.col_chunks[j], col_type) for j,col_type in enumerate(self.col_types)] for i in range(len(rows_variables))]
        for i,row in enumerate(self.rows):
            row_vars = []
            for j,qn in enumerate(row):
                qn.text = hf.strip_tags(self.rows_texts[i])
                qn.variables = [rows_variables[i][j]]
                if qn.type in [u'RadioButton', u'DropDownList', u'CheckBox']:
                    mask = [row[0] == u'ANSWER' for row in qn.qn_chunk]
                    rows = hf.select_rows(qn.qn_chunk, mask)
                    qn.answers_values = hf.select_cols(rows, [u'Setting Value'], lol=False)[1:]
                    mask = [row[0] == u'ANSWER' for row in qn.qn_chunk]
                    rows = hf.select_rows(qn.qn_chunk, mask)
                    qn.answers_texts = hf.select_cols(rows, [u'Text'], lol=False)[1:]
                    qn.answers_texts = [hf.strip_tags(item) for item in qn.answers_texts]
                    mask = [row[0] == u'SETTING' and row[1] == u'Visible' for row in qn.qn_chunk]
                    rows = hf.select_rows(qn.qn_chunk, mask)
                    qn.ans_is_vsbl = hf.select_cols(rows, [u'Setting Value'], lol=False)[1:]
                    qn.vsbl_inds = [k for k,v in enumerate(qn.ans_is_vsbl) if v == u'True'] if not self.show_inv else range(len(qn.ans_is_vsbl))
                    qn.answers = OrderedDict(zip(qn.answers_values,qn.answers_texts))
                    if qn.type == u'CheckBox':
                        qn.variables = [u'{}{}{}'.format(qn.variables[0],u'~C',k) for k in range(1,len(qn.answers_values)+1)] if len(qn.answers_values)>1 else qn.variables
                row_vars.append(qn.variables)
                self.variables += qn.variables
            self.rows_variables.append([v for sbl in row_vars for v in sbl])
            self.cols_variables.append(row_vars)
        self.cols_variables = [[v for sbl in row for v in sbl] for row in zip(*self.cols_variables)]
    
    def replace_vars(self):
        self.variables = [v.replace(u'~', u'' if self.repl_vars == True else u'_') for v in self.variables]
        self.rows_variables = [[v.replace(u'~', u'' if self.repl_vars == True else u'_') for v in row] for row in self.rows_variables]
        self.cols_variables = [[v.replace(u'~', u'' if self.repl_vars == True else u'_') for v in col] for col in self.cols_variables]
        for i,row in enumerate(self.rows):
            for j,qn in enumerate(row):
                if qn.type == u'CheckBox':
                    qn.repl_vars = self.repl_vars
                    qn.replace_vars()
    
    def set_data(self, data):
        self.data = hf.select_cols(data, self.variables)
        for row in self.rows:
            for qn in row:
                qn.set_data(data)
    
    def calc_stats(self):
        all_answers = self.data[1:]
        non_missing_answers = [answer for answer in all_answers if any(answer)]
        self.base = len(non_missing_answers)
        self.row_bases, self.in_row_cnts, self.in_row_prcnts = [], [], []
        for i,row in enumerate(self.rows):
            row_data = hf.select_cols(self.data, self.rows_variables[i])
            self.row_bases.append(sum(any(line) for line in row_data[1:]))
            in_row_cnts = []
            in_row_prcnts = []
            for qn in row:
                qn.calc_stats()
                in_row_cnts.append(qn.base)
                in_row_prcnts.append((100 * float(qn.base) / self.row_bases[-1]) if self.row_bases[-1] != 0 else 0.)
            self.in_row_cnts.append(in_row_cnts)
            self.in_row_prcnts.append(in_row_prcnts)
    
    def html_table(self):
        self.calc_stats()
        html_string = []
        col_nums_per_qn = []
        for i,qn in enumerate(self.rows[0]):
            if self.col_types[i] == u'TextAnswer':
                col_nums_per_qn.append(2)
            elif self.col_types[i] in [u'NumericAnswer', u'Slider']:
                col_nums_per_qn.append(6)
            else:
                col_nums_per_qn.append(2 * (len(qn.vsbl_inds) + 2))
        cols_num = 3 + sum(col_nums_per_qn) + 2
        html_string.append(u'<table id="{}">'.format(self.name))
        html_string.append(u'<tr>')
        html_string.append(u'<th colspan="3" class="header_base">{} /{}/ (Base:<a href="fltr_{}:[b.b]" style="color:white;">{}</a>)</th>'.format(self.name, self.type, self.name, self.base))
        html_string.append(u'<th colspan="{}" class="header_text">{}</th>'.format(cols_num - 3, self.text))
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th colspan="3" rowspan="2">Columns</th>')
        for i in range(len(self.cols_variables)):
            html_string.append(u'<th colspan="{}">[#{}] {} <span style="font-weight:normal;">/{}/<span></th>'.format(col_nums_per_qn[i], i + 1, self.cols_texts[i], self.col_types[i]))
        html_string.append(u'<th colspan="2" rowspan="2" class="header_base" style="text-align:center;">In Row<br>TOTAL</th>')
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        for i,qn in enumerate(self.rows[0]):
            html_string.append(u'<th colspan="2" class="header_base" style="text-align:center;">In Row</th>')
            if qn.type in [u'NumericAnswer', u'Slider']:
                html_string.append(u'<th rowspan="2">MIN</th>')
                html_string.append(u'<th rowspan="2">MAX</th>')
                html_string.append(u'<th rowspan="2">MS</th>')
                html_string.append(u'<th rowspan="2">SDV</th>')
            elif qn.type in [u'RadioButton', u'DropDownList', u'CheckBox']:
                for j,ans in enumerate(qn.answers.iteritems()):
                    if j in qn.vsbl_inds:
                        html_string.append(u'<th colspan="2">{}<span style="font-weight:normal;">[Code: {}]</span></th>'.format(ans[1]+u'<br>' if ans[1] else u'', ans[0]))
                html_string.append(u'<th colspan="2">TOTAL</th>')
        html_string.append(u'</tr>')
        html_string.append(u'<tr class="header_rest">')
        html_string.append(u'<th>Row</th><th>Text</th><th>Bases</th>')
        for i,qn in enumerate(self.rows[0]):
            html_string.append(u'<th class="header_base" style="text-align:center;">Counts</th><th class="header_base" style="text-align:center;">Percentages</th>')
            if qn.type in [u'RadioButton', u'DropDownList', u'CheckBox']:
                for j,ans in enumerate(qn.answers.iteritems()):
                    if j in qn.vsbl_inds:
                        html_string.append(u'<th>Counts</th><th>Percentages</th>')
                html_string.append(u'<th>Counts</th><th>Percentages</th>')
        html_string.append(u'<th class="header_base" style="text-align:center;">Counts</th><th class="header_base" style="text-align:center;">Percentages</th>')
        html_string.append(u'</tr>')
        for i,row in enumerate(self.rows):
            html_string.append(u'<tr>')
            html_string.append(u'<td>{}</td>'.format(i+1))
            html_string.append(u'<td class="row_labels">{}</td>'.format(self.rows_texts[i]))
            html_string.append(u'<td class="base_tot_cell"><a href="fltr_{}:[{}.b]">{}</a></td>'.format(self.name, i + 1, self.row_bases[i]))
            for j,qn in enumerate(row):
                html_string.append(u'<th class="header_base" style="text-align:center;"><a href="fltr_{}:[{}.{}:b]" style="color:white;">{}</a></th>'.format(self.name, i + 1, j + 1, self.in_row_cnts[i][j]))
                html_string.append(u'<th class="header_base" style="text-align:center;">{:.2f}%</th>'.format(self.in_row_prcnts[i][j]))
                if qn.type in [u'NumericAnswer', u'Slider']:
                    html_string.append(u'<td>{}</td>'.format(qn.min))
                    html_string.append(u'<td>{}</td>'.format(qn.max))
                    html_string.append(u'<td>{}</td>'.format(qn.mean_score))
                    html_string.append(u'<td>{}</td>'.format(qn.sdv))
                if qn.type in [u'RadioButton', u'DropDownList', u'CheckBox']:
                    for k,acp in enumerate(zip(qn.answers_values, qn.counts.values(), qn.percentages.values())):
                        if k in qn.vsbl_inds:
                            html_string.append(u'<td><a href="fltr_{}:[{}.{}:{}]">{}</a></td>'.format(self.name, i + 1, j + 1, acp[0], acp[1]))
                            html_string.append(u'<td>{}%</td>'.format(acp[2]))
                    cnts = sum(int(cnt) for cnt in qn.counts.values())
                    html_string.append(u'<th>{}</th>'.format(cnts))
                    prcnts = (100 * (float(cnts) / float(qn.base))) if qn.base else 0.
                    html_string.append(u'<th>{0:.0f}%</th>'.format(prcnts))
            tot_row_cnt = sum([qn.base for qn in row])
            tot_row_prcnt = 100 * float(tot_row_cnt) / self.row_bases[i] if self.row_bases[i] else 0.
            html_string.append(u'<th class="header_base" style="text-align:center;">{}</th>'.format(tot_row_cnt))
            html_string.append(u'<th class="header_base" style="text-align:center;">{0:.0f}%</th>'.format(tot_row_prcnt))
            html_string.append(u'</tr>')
        html_string.append(u'</table>'+ROWS_AFTER_TABLE*u'<br>')
        if self.logics:
            html_string.append(self.add_logics())        
        self.table = ''.join(html_string)
########################################################################################################################
########################################################################################################################
########################################################################################################################
########################################################################################################################

class QnrParser():
    
    def __init__(self, fl):
        self.file = fl
        self.questions = []
        t = time.time()
        if fl.endswith(u'.db'):
            with open(fl, 'rb') as _file:
                with lz4_frame.open(_file) as f:
                    self.data = json.loads(f.read())
        elif fl.endswith(u'.xlsx'):
            with open_workbook(self.file) as wb:
                ws = wb.sheet_by_name(u'Questionnaire')
                rows = xrange(ws.nrows)
                get_rows = ws.row_values
                self.data = [get_rows(row) for row in rows]
        t = time.time() - t
        print u'Questionnaire Imported: (lines:{}, variables:{}) in {:.2f} secs'.format(len(self.data), len(self.data[0]), t)
        headers = self.data[0]
        data = self.data[1:]
        inds = [ind for ind,row in enumerate(data) if row[0] == u'BLOCK' or row[0] == u'QUESTION' or row[0] == u'QUESTIONNAIRE']
        self.chunks = [[headers]+qn for qn in hf.split_to_chunks(data, inds)]
    #    self.bl_chunks = [chunk for chunk in self.chunks if chunk[1][0] == u'BLOCK']
    #    self.qnr_chunks = [chunk for chunk in self.chunks if chunk[1][0] == u'QUESTIONNAIRE']
        self.qn_chunks = [chunk for chunk in self.chunks if chunk[1][0] == u'QUESTION']
    
    def make_questions(self):
        self.questions.append(CASEID())
        self.questions[-1].parse_question()
        self.questions.append(Date())
        self.questions[-1].parse_question()
        self.questions.append(DURATION())
        self.questions[-1].parse_question()
        self.questions.append(Disposition())
        self.questions[-1].parse_question()
        for qn_chunk in self.qn_chunks:
            qn_type = hf.select_cols(qn_chunk, ['Type'], lol=False)[1]
            q = None
            if qn_type == u'RadioButton':
                q = RadioButton(qn_chunk, qn_type)
            elif qn_type == u'CheckBox':
                q = CheckBox(qn_chunk, qn_type)
            elif qn_type == u'ChoiceGrid':
                q = ChoiceGrid(qn_chunk, qn_type)
            elif qn_type == u'NumericAnswer':
                q = NumericAnswer(qn_chunk, qn_type)
            elif qn_type == u'RunningTotal':
                q = RunningTotal(qn_chunk, qn_type)
            elif qn_type == u'NumericRanking':
                q = NumericRanking(qn_chunk, qn_type)
            elif qn_type == u'DragDropRanking':
                q = DragDropRanking(qn_chunk, qn_type)
            elif qn_type == u'DropDownList':
                q = DropDownList(qn_chunk, qn_type)
            elif qn_type == u'NetPromoter':
                q = NetPromoter(qn_chunk, qn_type)
            elif qn_type == u'TextAnswer':
                q = TextAnswer(qn_chunk, qn_type)
            elif qn_type == u'Slider':
                q = Slider(qn_chunk, qn_type)
            elif qn_type == u'HybridGrid':
                q = HybridGrid(qn_chunk, qn_type)
            if q is not None:
                q.parse_question()
                self.questions.append(q)

class DataParser():
    
    def __init__(self, fl, qns_parsed):
        self.repl_vars = None
        self.file = fl
        self.qns_parsed = qns_parsed
        t = time.time()
        if fl.endswith(u'.db'):
            with open(fl, 'rb') as _file:
                with lz4_frame.open(_file) as f:
                    dt = json.loads(f.read())
                    self.repl_vars = dt['repl_vars']
                    self.data = dt['data']
        elif fl.endswith(u'.csv'):
            with open(fl) as f:
                rdr = reader(f, delimiter=',')
                self.data = [[unicode(item, encoding='utf-8') for item in row] for row in rdr]
        elif fl.endswith(u'.xlsx'):
            with open_workbook(self.file) as wb:
                ws = wb.sheet_by_name(u'Sheet1')
                rows = xrange(ws.nrows)
                get_rows = ws.row_values
                self.data = [get_rows(row) for row in rows]
        t = time.time() - t
        print u'Data Imported: (lines:{}, variables:{}) in {:.2f} secs'.format(len(self.data), len(self.data[0]), t)
        self.data[0][0] = self.data[0][0].replace(u'\ufeff', u'')

    def match_data_to_questions(self, repl_vars):
        t = time.time()
        for qn in self.qns_parsed:
            qn.repl_vars = repl_vars
            if qn.type in [u'CASEID', u'Duration', u'Disposition', u'CheckBox', u'ChoiceGrid',
                           u'NumericRanking', u'DragDropRanking', u'HybridGrid']:
                qn.replace_vars()
            qn.set_data(self.data)
            if qn.type == u'Date': qn.set_answers()
        t = time.time() - t
        print u'Data Matched in {:.2f} secs'.format(t)

class Previewer():
    
    def __init__(self):
        # Filter expression from Line edit
        self.fldt_text = u''
        # the imported questionnaire file
        self.qnr_file = u''
        # the imported data file
        self.data_file = u''
        # the Table of Contents html string
        self.toc = []
        # list holding the strings describing each filter that has been applied
        self.filters = []
        # list holding the html strings for each table
        self.tables = []
        # the html tables string to preview in the webView
        self.html = u''
        # list holding the current data with the corresponding reports as tuples
        self.report_tracks = []
        # The list that contains the parsed question instances with their data
        self.questions = []
        # The list that contains the selected question instances with their data
        self.selected_questions = []
        # data parsed from import file
        self.initial_data = None
        # instasnce of Qnr Parser
        self.QnrP = None
        # questionnaire data
        self.qnr_data = None
        # current data. Filtered or not
        self.data = None
        # True or False according to the value of the radiobutton in the form and the imported data file
        self.repl_vars = None
        # variable to indicate who is getting the application
        self.HRH = None
        # variable to indicate if logics will be displayed
        self.logics = None
    
    def parse_questionnaire(self, fl):
        self.QnrP = QnrParser(fl)
        self.qnr_data = self.QnrP.data
        t = time.time()
        self.QnrP.make_questions()
        t = time.time() - t
        print u'Make Questions: {:.2f} secs'.format(t)
        # filter names
#        excl_qn_names = [u'psid', u'PSID', u'COMPLETED_URL', u'QUOTAFULL_URL', u'SCREENOUT_URL']
        excl_qn_names = []
#        if not self.HRH:
#            excl_qn_names = [u'ID', u'psid', u'PSID', u'COMPLETED_URL', u'QUOTAFULL_URL', u'SCREENOUT_URL']
        # filter types
        qn_types = [u'CASEID', u'Date', u'Duration', u'Disposition', u'ChoiceGrid', u'RadioButton', u'CheckBox', u'NumericAnswer', u'RunningTotal', u'NumericRanking', u'DragDropRanking', u'DropDownList', u'NetPromoter', u'TextAnswer', u'Slider', u'HybridGrid']
#        if not self.HRH:
#            qn_types = [_type for _type in qn_types if _type not in [u'CASEID', u'Duration']]
#        if not self.date:
#            qn_types = [_type for _type in qn_types if _type not in [u'Date']]
        self.questions = [qn for qn in self.QnrP.questions if qn.name not in excl_qn_names and qn.type in qn_types]
        for qn in self.questions:
            if qn.type not in [u'CASEID', u'Date', u'Duration', u'Disposition']:
                qn.logics = self.logics
            else:
                qn.logics = False
    
    def parse_data(self, fl):
        DtP = DataParser(fl, self.questions)
        if DtP.repl_vars is not None: self.repl_vars = DtP.repl_vars
        DtP.match_data_to_questions(self.repl_vars)
        self.initial_data = DtP.data
        self.data = self.initial_data
    
    def set_data(self, data):
        self.data = data
        for qn in self.questions:
            qn.set_data(data)
    
    def filter_data(self, url_str=None):
        t = time.time()
        if url_str is not None or self.fldt_text:
            expr = Word(''.join([c for c in printables if c not in '&|~()']))
            # https://stackoverflow.com/questions/10805368/passing-user-defined-argument-to-setparseaction-in-pyparsing
            expression = operatorPrecedence(expr.setParseAction(lambda tokens: hf.ConditionString(tokens, self.questions)),
                                            [(u'~', 1, opAssoc.RIGHT, hf.SearchNot),
                                             (u'&', 2, opAssoc.LEFT, hf.SearchAnd),
                                             (u'|', 2, opAssoc.LEFT, hf.SearchOr)])
            if url_str is not None:
                filter_string = url_str.replace(u'fltr_', '')
                self.fldt_text = u''
            elif self.fldt_text:
                filter_string = u','.join([item for item in ''.join(self.fldt_text.split()).split(u',') if item])
            evalStack = (expression + stringEnd).parseString(filter_string)[0]
            filter_string = evalStack.to_str()
            filter_string = u'({})'.format(filter_string) if any([op in filter_string for op in u'~&|']) else filter_string
            filter_string = filter_string.replace(u'~', u' ~ ').replace(u'&', u' & ').replace(u'|', u' | ').replace(u'( ', u'(')
            if self.fldt_text:
                self.filters = []
                if self.report_tracks:
                    self.report_tracks = []
                    self.set_data(self.initial_data)
            self.filters.append(filter_string)
            mask = [True] + evalStack.eval()
            data = hf.select_rows(self.data, mask)
        else:
            self.filters = []
            data = self.initial_data
        self.set_data(data)
        t = time.time() - t
        print u'Data Filtered in {:.2f} secs'.format(t)
    
    def cnt_five_or_more(self):
        excl_types = [u'Date', u'Duration', u'Disposition']
        questions = [qn for qn in self.QnrP.questions if qn.type not in excl_types]
        q_data_of_each_case = zip(*[q.data[1:] for q in questions])
        case_id_q_answered = []
        for case in q_data_of_each_case:
            case_id = case[0][0]
            other_questions_data = case[1:]
            questions_answered = [q.name for q, q_data in zip(questions[1:], other_questions_data) if any(q_data)]
            if len(questions_answered) >= 5:
                case_id_q_answered.append(u'{}~{}~{}'.format(case_id, len(questions_answered), ','.join(questions_answered)))
        self.five_or_more = len(case_id_q_answered)
        return self.five_or_more, '\n'.join(case_id_q_answered).encode('utf-8')
    
    def make_preview(self):
#        d = OrderedDict([])
        t_tot = time.time()
        self.tables = []
        self.toc = []
        for qn in self.selected_questions:
#            t = time.time()
            qn.html_table()
            self.toc.append((u'<a href="#{}"><b>{}</b></a>'+(u' - ' if qn.text else '')+'{}<br><hr>').format(qn.name, qn.name, qn.text))
            if qn.table:self.tables.append(qn.table)
#            t = time.time() - t
#            d[qn.name] = t
        self.html = hf.make_html_doc(toc='\n'.join(self.toc), fltr=self.filters, tables=self.tables)
        t_tot = time.time() - t_tot
#        d[u'Total'] = t_tot
#        for k,v in d.iteritems():
#            print u'{},{},{:.2f}%'.format(k,v,int(100. * v / d[u'Total']) if d[u'Total'] else 0.)
        print u'Preview Made in {:.2f} secs'.format(t_tot)
    
    def track_report(self, url=None):
        if url is None:
            self.report_tracks.append((self.data, self.html))
        elif url == u'fltr_OFF':
            self.filters, self.report_tracks = self.filters[:-1], self.report_tracks[:-1]
            if self.report_tracks:
                self.set_data(self.report_tracks[-1][0])
                self.html = self.report_tracks[-1][1]
            else:
                self.set_data(self.initial_data)
                self.make_preview()
                self.report_tracks.append((self.data, self.html))
        else:
            self.filters, self.report_tracks = [], []
            self.set_data(self.initial_data)
            self.make_preview()
            self.report_tracks.append((self.data, self.html))




if __name__ == '__main__':
#    print 'CLASS: '+qn.__class__.__name__

    print 'ok'