# -*- coding: utf-8 -*-
import os
import sys
import datetime
#import cPickle as pickle
#import bz2
from lz4 import frame as lz4_frame
import json
import time
from PyQt4 import QtGui
from PyQt4.QtWebKit import QWebPage
import Parse_Questionnaire as pq
import Helper_Functions as hf
from TEST_Form import Ui_Form

######################### Expired Date ################################
exp_date = u'30/12/2131 10:00:00'
exp_date = datetime.datetime.strptime(exp_date, '%d/%m/%Y %H:%M:%S') # day: zero-padded (01), month: zero-padded (01)
                                                                     # year: with century (2019)
                                                                     # hour: (24-hour clock) zero-padded (08)
                                                                     # minute: zero-padded (01)
                                                                     # second: zero-padded (01)
now_date = datetime.datetime.now()
#######################################################################

class MyForm(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        # webView
        self.wv = self.ui.webView
        self.wv.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.wv.linkClicked.connect(self.handleLinkClicked)
        # other widgets
        self.lst = self.ui.listWidget
        self.fldt = self.ui.fldt
        self.from_vxc_rb = self.ui.from_vxc_rb
        self.from_sav_rb = self.ui.from_sav_rb
        self.qn_fl_btn = self.ui.qn_file_btn
        self.qlbl = self.ui.qn_file_lbl
        self.dt_fl_btn = self.ui.dt_file_btn
        self.dlbl = self.ui.data_file_lbl
        self.prv_btn = self.ui.prv_btn
        self.exp_btn = self.ui.exp_btn
        # Button for exporting to .db files
        self.expbn_btn = self.ui.expbn_btn
        self.olbl = self.ui.outputLabel
        # initial directory for selecting files
        self.init = "C:\\"
        # connections
        self.qn_fl_btn.clicked.connect(self.import_questionnaire)
        self.dt_fl_btn.clicked.connect(self.import_data)
        self.prv_btn.clicked.connect(self.preview_selected)
        self.exp_btn.clicked.connect(self.export_preview)
        self.expbn_btn.clicked.connect(self.export_dbs)
        self.from_vxc_rb.setChecked(True)
        # main object
        self.Pv = pq.Previewer()
        self.Pv.olbl = self.olbl
        #####################################################################
        self.Pv.HRH = True # variable to indicate who is getting the application
        self.Pv.date = True # variable to indicate if the date question will be displayed
        self.Pv.duration = True # variable to indicate if the duration question will be displayed
        self.Pv.logics = True # variable to indicate if logics will be displayed
        self.Pv.print_cost = False # variable to indicate if cost will be displayed
        ########## Other ##########
        self.qnr_cost = 0.4
        self.print_five_report = False
        self.print_five_report_folder = r'C:\Users\user\Desktop'
        #####################################################################
        if not self.Pv.HRH: self.ui.frame.setEnabled(False)

    def load_html(self, html):
        self.wv.setHtml(u'Processing HTML...')
        self.wv.setHtml(html)
        app.processEvents()

    def import_questionnaire(self):
        file_types = 'DataBase files *.db;;Excel files *.xlsx' if self.Pv.HRH else 'DataBase files *.db'
        imported_qnr = unicode(QtGui.QFileDialog.getOpenFileName(self, 'Open Questionnaire File', self.init, file_types))
        if not imported_qnr: return
        self.lst.clear()
        hf.print_output(u'Processing Questionnaire File...', self.olbl, app)
        date = os.path.getmtime(imported_qnr)
        fl = os.path.split(imported_qnr)[-1]
        try:
            self.Pv.parse_questionnaire(imported_qnr)
        except Exception:
            hf.print_output(u'Error parsing questionnaire. Please check your input file.', self.olbl, app)
            return
#        if self.Pv.HRH:
#            self.lst.addItem((u'[{} ({})]').format(u'_CASEID_', u'CASEID'))
#        if self.Pv.date:
#            self.lst.addItem((u'[{} ({})]').format(u'_DATE_', u'Date'))
#        if self.Pv.HRH:
#            self.lst.addItem((u'[{} ({})]').format(u'_DURATION_', u'Duration'))
#
#        dsp_ind = [i for i,qn in enumerate(self.Pv.questions) if qn.type == u'Disposition'][0]
#        dsp = self.Pv.questions[dsp_ind]
#        self.lst.addItem((u'[{} ({})]').format(dsp.name, dsp.type))
#        for i,qn in enumerate(self.Pv.questions[dsp_ind + 1:]):
#            tp = qn.type if qn.type != u'ChoiceGrid' else u'{} - {}'.format(qn.type, {u'RadioButton':u'S', u'CheckBox':u'M'}[qn.grid_type])
#            self.lst.addItem((u'#{} - {} ({})').format(hf.toUc(str(i+1)), qn.name, tp))

        excl_qn_names = [u'psid', u'PSID', u'COMPLETED_URL', u'QUOTAFULL_URL', u'SCREENOUT_URL']
        if not self.Pv.HRH:
            excl_qn_names.append(u'_CASEID_')
            excl_qn_names.append(u'ID')
        if not self.Pv.date:
            excl_qn_names.append(u'_DATE_')
        if not self.Pv.duration:
            excl_qn_names.append(u'_DURATION_')

        displayed_questions = [q for q in self.Pv.questions if q.name not in excl_qn_names]

        dsp_ind = [i for i,qn in enumerate(displayed_questions) if qn.type == u'Disposition'][0]
        for q in displayed_questions[:dsp_ind+1]:
            self.lst.addItem((u'[{} ({})]').format(q.name, q.type))
        for i,qn in enumerate(displayed_questions[dsp_ind+1:]):
            tp = qn.type if qn.type != u'ChoiceGrid' else u'{} - {}'.format(qn.type, {u'RadioButton':u'S', u'CheckBox':u'M'}[qn.grid_type])
            self.lst.addItem((u'#{} - {} ({})').format(hf.toUc(str(i+1)), qn.name, tp))

        self.Pv.qnr_file = u'{} (Last date modified: {})'.format(fl, hf.day_str(date))
        hf.print_output(self.Pv.qnr_file, self.qlbl, app)
        hf.print_output(u'Questionnaire parsed', self.olbl, app)
        self.load_html(u'')

    def import_data(self):
        if self.Pv.questions:
            file_types = 'DataBase files *.db;;Csv files *.csv;;Excel files *.xlsx' if self.Pv.HRH else 'DataBase files *.db'
            imported_data = unicode(QtGui.QFileDialog.getOpenFileName(self, 'Open Data File', self.init, file_types))
            if not imported_data: return
            hf.print_output(u'Processing Data File...', self.olbl, app)
            date = os.path.getmtime(imported_data)
            fl = os.path.split(imported_data)[-1]
            if not imported_data.endswith(u'.db'):
                self.Pv.repl_vars = True if self.from_sav_rb.isChecked() else False
            self.Pv.parse_data(imported_data)
#            try:
#                self.Pv.parse_data(imported_data)
#            except Exception:
#                hf.print_output(u'Error parsing data. Please check your input file.', self.olbl, app)
#                return
            self.Pv.data_file = u'{} (Last date modified: {})'.format(fl, hf.day_str(date))
            hf.print_output(self.Pv.data_file, self.dlbl, app)
            cnt_five_num, cnt_five_rep = self.Pv.cnt_five_or_more()

            if self.print_five_report:
                with open(os.path.join(self.print_five_report_folder, 'report.txt'), 'w') as f:
                    f.write(cnt_five_rep)

            cnt_five_txt = u'  //  (Cases with >=5 questions answered: {} = {}€)'.format(cnt_five_num, self.qnr_cost*cnt_five_num) if self.Pv.print_cost else u''
            hf.print_output(u'Data Matched - Current base: {}{}'.format(len(self.Pv.data) - 1, cnt_five_txt), self.olbl, app)
            self.load_html(u'')
        else:
            hf.print_output(u'No Questionnaire parsed. Please import Questionnaire first and then import Data.', self.olbl, app)

    def preview_selected(self):
        selected_q_names = []
        for q in self.lst.selectedIndexes():
            q_txt = hf.toUc(q.data().toString()) if not isinstance(q.data(), basestring) else hf.toUc(q.data())
            if q_txt.startswith('#'):
                q_name = q_txt.split()[2]
            else:
                q_name = q_txt.split()[0][1:]
            selected_q_names.append(q_name)
        if selected_q_names and self.Pv.data is not None:
            self.Pv.fldt_text = hf.toUc(self.fldt.text()).strip()
            self.fldt.setText(u'')
            hf.print_output(u'Processing Preview...', self.olbl, app)
            self.Pv.selected_questions = [qn for qn in self.Pv.questions if qn.name in selected_q_names]
            for item in self.lst.selectedItems():
                item.setSelected(False)
            try:
                self.Pv.filter_data()
            except Exception:
                hf.print_output(u'Error in filtering data. Please check your input.', self.olbl, app)
                return
            self.Pv.make_preview()
            # try:
            #     self.Pv.make_preview()
            # except Exception:
            #     hf.print_output(u'Error in making preview. Please check your input.', self.olbl, app)
            #     return
            try:
                self.Pv.track_report()
            except Exception:
                hf.print_output(u'Error in tracking report. Please check your input.', self.olbl, app)
                return
            self.load_html(self.Pv.html)
            cnt_five_num, cnt_five_rep = self.Pv.cnt_five_or_more()
            cnt_five_txt = u'  //  (Cases with >=5 questions answered: {} = {}€)'.format(cnt_five_num, self.qnr_cost*cnt_five_num) if self.Pv.print_cost else u''
            hf.print_output(u'Preview of selected questions completed - Current base: {}{}'.format(len(self.Pv.data) - 1, cnt_five_txt), self.olbl, app)
        else:
            hf.print_output(u'Please select data to parse and questions to preview', self.olbl, app)

    def export_preview(self):
        if self.Pv.report_tracks:
            fl = unicode(QtGui.QFileDialog.getSaveFileName(self, u'Save Current Preview', u'preview.html', u'HTML File (*.html)'))
            if not fl: return
            hf.print_output(u'Processing...', self.olbl, app)
            with open(fl, 'w') as f:
                f.write(hf.strip_fltr_tags(self.Pv.report_tracks[-1][1]).encode('utf-8'))
            hf.print_output(u'Export Complete', self.olbl, app)
        else:
            hf.print_output(u'No Preview to save', self.olbl, app)

    def export_dbs(self):
        if self.Pv.questions and self.Pv.data:
            fld = unicode(QtGui.QFileDialog.getExistingDirectory(self, "Select Directory"))
            if not fld: return
            hf.print_output(u'Processing...', self.olbl, app)
#            with bz2.BZ2File(hf.save_filename(u'Data.db', fld), 'wb') as f:
#                pickle.dump(d_to_store, f)
#            with open(fl, 'rb') as f:
#                d = pickle.load(bz2.BZ2File(fl, 'rb'))
            fl = hf.save_filename(u'Questionnaire.db', fld)
            t = time.time()
            with open(fl, 'wb') as _file:
                with lz4_frame.open(_file, mode='wb') as f:
                    f.write(json.dumps(self.Pv.qnr_data))
            t = time.time() - t
            print u'Questionnaire Stored: (lines:{}, variables:{}) in {:.2f} secs'.format(len(self.Pv.qnr_data), len(self.Pv.qnr_data[0]), t)
            data_dict = {'repl_vars':self.Pv.repl_vars, 'data':self.Pv.data}
            fl = hf.save_filename(u'Data.db', fld)
            t = time.time()
            with open(fl, 'wb') as _file:
                with lz4_frame.open(_file, mode='wb') as f:
                    f.write(json.dumps(data_dict))
            t = time.time() - t
            print u'Data Stored: (lines:{}, variables:{}) in {:.2f} secs'.format(len(self.Pv.data), len(self.Pv.data[0]), t)
            hf.print_output(u'Export Complete', self.olbl, app)
        else:
            hf.print_output(u'Import Questionnaire and Data files to export', self.olbl, app)

    def handleLinkClicked(self, url):
        url_str = hf.toUc(url.toString())
        if not url_str.startswith(u'fltr_') :
            self.wv.load(url)
        else:
            hf.print_output(u'Processing Filter...', self.olbl, app)
            if u'fltr_OFF' in url_str:
                self.Pv.track_report(url=url_str)
            else:
                self.Pv.filter_data(url_str)
                self.Pv.make_preview()
                self.Pv.track_report()
            self.load_html(self.Pv.html)
            cnt_five_num, cnt_five_rep = self.Pv.cnt_five_or_more()
            cnt_five_txt = u'  //  (Cases with >=5 questions answered: {} = {}€)'.format(cnt_five_num, self.qnr_cost*cnt_five_num) if self.Pv.print_cost else u''
            hf.print_output(u'Filter completed - Current base: {}{}'.format(len(self.Pv.data) - 1, cnt_five_txt), self.olbl, app)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    myapp = MyForm()
    myapp.show()

    if now_date > exp_date:
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Critical)
        msg.setWindowTitle(u' ')
        msg.setText(u'Trial Period Expired')
        msg.setStandardButtons(QtGui.QMessageBox.Ok)
        msg.exec_()
        sys.exit()

    sys.exit(app.exec_())




