# -*- coding: utf-8 -*-
import os
import sys
import Helper_Functions as hf

class ParseLogics():
    def __init__(self, q_chunk):
       self.q_chunk = q_chunk

    def to_list_of_dicts(self, q_chunk):
        headers = q_chunk[0]
        data = q_chunk[1:]
        if data:
            return [{x:y for x,y in zip(headers, line)} for line in data]
        else:
            return [{x:'' for x in headers}]
    
    def split_to_chunks(self, q_chunk):
        headers = q_chunk[0]
        data = q_chunk[1:]        
        inds = [ind for ind,row in enumerate(data) if row[0] == u'QUESTION' or row[0].endswith(u'LOGIC') or row[0].endswith(u'ACTION')]
        return [[headers]+chunk for chunk in hf.split_to_chunks(data, inds)]
    
    def print_chunk(self, q_chunk):
        '''List of dicts as input'''
        ordered_header = [u'Item', u'Name', u'Text', u'Type', u'Setting Value']
        output = []
        output.append(','.join(ordered_header))
        if len(q_chunk) > 0:
            for d in q_chunk:
                output.append(u','.join([d[x] for x in ordered_header]))
        return u'\n'.join(output)
        
    def extract_condition(self, chunk):
        op_dict = {'Equals':'=', 'DifferentThan':'!=', 'LessThan':'<', 'MoreThan':'>', 'LessThanOrEqual':'<=', 'MoreThanOrEqual':'>=',
                  'Contains':'Contains', 'DoesNotContain':'Does Not Contain', 'Empty':'Is Empty', 'NotEmpty':'Is Not Empty'}
        chunk_type_line = [x for x in chunk if x['Item'] == 'EXECUTIONCONDITION' or x['Item'].endswith('LOGIC')]
        if not chunk_type_line:
            return ''
        chunk_type_line = chunk_type_line[0]
        chunk_type_txt = chunk_type_line['Type']
        if chunk_type_txt == 'Advanced':
            return chunk_type_line['Setting Value']
        else:
            boolean_operator = chunk_type_txt.upper()
            condition_lines = [' '.join([line['Name'], op_dict[line['Type']], line['Setting Value']]).strip() for line in chunk if line['Item'] == 'CONDITION']
            return (' {} '.format(boolean_operator)).join(condition_lines)
        
    def chunk_logic(self, chunk, html=False):
        '''List of dicts as input'''
        space_char = u'&nbsp;' if html else u' '
        sep_char = u'<~br~>' if html else u'\n'
        output = []
        chunk_type_line = chunk[0]
        chunk_type_txt = chunk_type_line['Item']
        if chunk_type_txt == 'QUESTION':
            # PLAIN
            choice_elim_if_ans = [x['Setting Value'] for x in chunk if x['Name'] == 'EliminateChoicesIfVariablesAnswered']
            choice_elim_if_not_ans = [x['Setting Value'] for x in chunk if x['Name'] == 'EliminateChoicesIfVariablesNotAnswered']
            choice_exclude = [x['Setting Value'] for x in chunk if x['Name'] == 'EliminationExcludedFields']
            # GRID
            row_elim_if_ans = [x['Setting Value'] for x in chunk if x['Name'] == 'RowEliminationIfVariablesAnswered']
            row_elim_if_not_ans = [x['Setting Value'] for x in chunk if x['Name'] == 'RowEliminationIfVariablesNotAnswered']
            row_exclude = [x['Setting Value'] for x in chunk if x['Name'] == 'RowEliminationExcluded']
            
            if row_elim_if_ans:
                output.append(u'Eliminate rows if answered in: {}'.format(row_elim_if_ans[0]))
            if row_elim_if_not_ans:
                output.append(u'Eliminate rows if NOT answered in: {}'.format(row_elim_if_not_ans[0]))
            if row_exclude:
                output.append(u'Exclude rows: '.format(choice_exclude[0]))
            
            if choice_elim_if_ans:
                output.append(u'Eliminate choices/columns if answered in: {}'.format(choice_elim_if_ans[0]))
            if choice_elim_if_not_ans:
                output.append(u'Eliminate choices/columns if NOT answered in: {}'.format(choice_elim_if_not_ans[0]))
            if choice_exclude:
                output.append(u'Exclude choices/columns: {}'.format(choice_exclude[0]))
        else:
            condition = self.extract_condition(chunk)
            if chunk_type_txt.endswith('LOGIC'):
                show_hide = u'SHOW' if chunk_type_txt.startswith('ASK') else u'HIDE'
                # condition = chunk_type_line['Setting Value']
                output.append(u'{} if {}'.format(show_hide, condition))
            elif chunk_type_txt.endswith('ACTION'):
                when = u'Before' if chunk_type_txt.startswith('PRE') else u'After'
                # condition = [x['Setting Value'] for x in chunk if x['Item'] == 'EXECUTIONCONDITION']
                # condition = u'if {} '.format(condition[0]) if condition else ''            
                condition = u'if {}'.format(condition+' ' if condition else condition)
                action_type = chunk_type_line['Type']
                if action_type == 'ExitSurvey':
                    status = [x for x in chunk if x['Type'] == 'Status'][0]['Setting Value']
                    output.append(u'{}: {}-> {}'.format(when, condition, status))
                elif action_type == 'BranchTo':
                    status = [x for x in chunk if x['Type'] == 'Question'][0]['Setting Value']
                    output.append(u'{}: {}-> {}'.format(when, condition, status))
                elif action_type == 'ComputeVariable':
                    var_name = [x for x in chunk if x['Type'] == 'CalculatedVariableName'][0]['Setting Value']
                    value_type = [x for x in chunk if x['Type'] == 'ValueType'][0]['Setting Value'].replace('Variable', 'Value')
                    value = [x for x in chunk if x['Type'] == 'Value'][0]['Setting Value']
                    strip_message = '' if value.strip() == value else ' (UNSTRIPPED VALUE)'
                    output.append(u'{}: {}-> Compute ({}) {} = {}{}'.format(when, condition, value_type, var_name, value, strip_message))
                elif action_type == 'SetVariableValue':
                    var_name = [x for x in chunk if x['Type'] == 'Variable'][0]['Setting Value']
                    value_type = [x for x in chunk if x['Type'] == 'ValueType'][0]['Setting Value'].replace('Variable', 'Value')
                    value = [x for x in chunk if x['Type'] == 'Value'][0]['Setting Value']
                    strip_message = '' if value.strip() == value else ' (UNSTRIPPED VALUE)'
                    output.append(u'{}: {}-> Set Value ({}) {} = {}{}'.format(when, condition, value_type, var_name, value, strip_message))
                elif action_type == 'Selection':
                    mentions = [x['Setting Value'] for x in chunk if x['Type'] == 'Mention']
                    selection_vars = [x['Setting Value'] for x in chunk if x['Item'] == 'SELECTIONVARIABLE']
                    values = [x['Setting Value'] for x in chunk if x['Item'] == 'SELECTION']
                    inclusion_formulas = [x['Setting Value'] for x in chunk if x['Type'] == 'InclusionFormula']
                    txt_1 = [u'{}: {}-> Selection'.format(when, condition)]
                    txt_2 = [u'{}{} mention {}'.format((len(when)+2) * space_char, m, s) for m,s in zip(mentions, selection_vars)]
                    txt_3 = [u'{}{} if {}'.format((len(when)+2) * space_char, v, c) for v,c in zip(values, inclusion_formulas)]
                    output.append(sep_char.join(txt_1+txt_2+txt_3))
        output = sep_char.join(output)
        output = output.replace(u'<br>',u'&lt;br&gt;')
        output = output.replace(u'<~br~>',u'<br>')
        return output
        
    def question_logics(self, html=False):
        sep_char = u'<br>' if html else u'\n'
        chunks = self.split_to_chunks(self.q_chunk)
        chunks = [self.to_list_of_dicts(chunk) for chunk in chunks]
        output = [self.chunk_logic(chunk, html) for chunk in chunks]
        output = [x for x in output if x.strip()]
        output = sep_char.join(output)
        output = output.replace(u'->',u'→')
        return output


if __name__ == '__main__':
    from Parse_Questionnaire import QnrParser as qp
    fld = r'C:\ANASTASIS\HRH-C\online_studies\online\2020\17344_EKE_Nestle_Sep20\DATA\PREVIEW'
    fl = 'EKE_NESTLE_Questionnaire.xlsx'
    qname = 'Q1B'
    # fld = r'C:\ANASTASIS\HRH-C\online_studies\online\2020\17342_I0154_(Truberries)\DATA\PREVIEW'
    # fl = 'I0154_Questionnaire.xlsx'
    # qname = 'Q23'
    fl = os.path.join(fld,fl)
    qnr = qp(fl)
    q_chunk = [chunk for chunk in qnr.qn_chunks if chunk[1][1] == qname][0]
    pl = ParseLogics(q_chunk)
    
    
    q_chunks = pl.split_to_chunks(q_chunk)
    # for ch in q_chunks:
    #     d = pl.to_list_of_dicts(ch)
    #     print d
    #     print(pl.print_chunk(d).encode('utf-8'))
    #     print
    for ch in q_chunks:
        d = pl.to_list_of_dicts(ch)
        print(pl.print_chunk(d).encode('utf-8'))
        print(50*'-')
    print(50*'=')
    print(pl.question_logics().encode('utf-8'))
    print(50*'=')
    print(50*'=')
        
    
    # print(pl.question_logics().encode('utf-8'))
    

