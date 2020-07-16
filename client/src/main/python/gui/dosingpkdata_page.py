"""
.. module:: dosingpkdata_page
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import csv
import io
from os import access, R_OK
from os.path import isfile
from collections import defaultdict

from PyQt5.QtWidgets import (
    QTableView,
    QWizardPage,
    QHBoxLayout,
    QVBoxLayout,
    QGroupBox,
    QPushButton,
    QFileDialog,
)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import Qt

from config.consts import PKDATA_FIELDS, SIM_TYPES_INFO, NULL_PKDATA_STRUCT

from utils import shared, db_utils
from utils.gen_utils import text_to_list, list_to_str

SimInfo = shared.SimInfo()


class DosingPKDataPage(QWizardPage):
    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)
        self.setup_ui()

    def setup_ui(self):
        hlist = sorted(PKDATA_FIELDS.values(), key=lambda x: x[1])
        self._pkdata_fields = [lbl for (lbl, _) in hlist]
        vlist = [(varname, col) for varname, (_, col) in PKDATA_FIELDS.items()]
        self._pkdata_vars = [v for (v, c) in sorted(vlist, key=lambda x: x[1])]
        self._sims_using_pkdata = [
            k for k, v in SIM_TYPES_INFO.items() if v["uses_pkdata"]
        ]

        self.pkdata_table_view = QTableView(self)
        self.pkdata_model = QStandardItemModel(self)
        self.pkdata_table_view.setModel(self.pkdata_model)
        self.pkdata_model.setHorizontalHeaderLabels(self._pkdata_fields)

        # layouts for buttons
        button_layout = QVBoxLayout()
        self.button_box = QGroupBox()
        self.button_box.setLayout(button_layout)

        # edit data sets
        self.edittable_box = QGroupBox("Edit table")
        edittable_layout = QVBoxLayout()
        self.edittable_box.setLayout(edittable_layout)
        add_dataset_button = QPushButton("Add Row")
        edittable_layout.addWidget(add_dataset_button)
        add_dataset_button.clicked.connect(self.add_dataset)
        remove_dataset_button = QPushButton("Remove Row")
        edittable_layout.addWidget(remove_dataset_button)
        clear_datasets_button = QPushButton("Remove All Rows")
        edittable_layout.addWidget(clear_datasets_button)
        remove_dataset_button.clicked.connect(self.remove_selected_row)
        clear_datasets_button.clicked.connect(self.remove_rows)

        # load and save dataset
        self.loadsave_box = QGroupBox("Load / Save")
        loadsave_layout = QVBoxLayout()
        self.loadsave_box.setLayout(loadsave_layout)
        import_datasets_button = QPushButton("Load Data")
        loadsave_layout.addWidget(import_datasets_button)
        import_datasets_button.clicked.connect(self.import_datasets)
        save_data_button = QPushButton("Save Data")
        loadsave_layout.addWidget(save_data_button)
        save_data_button.clicked.connect(self.save_data)

        edittable_layout.setAlignment(Qt.AlignTop)
        loadsave_layout.setAlignment(Qt.AlignTop)

        button_layout.addWidget(self.edittable_box)
        button_layout.addWidget(self.loadsave_box)

        # page layout
        page_layout = QHBoxLayout()

        page_layout.addWidget(self.pkdata_table_view)
        page_layout.addWidget(self.button_box)

        self.setLayout(page_layout)
        self.setTitle("Dosing and Pharmacokinetic Data")

        # add tooltips
        dkey = "dosing_type"
        varname_to_col = {vname: col for vname, (_, col) in PKDATA_FIELDS.items()}
        dosetype_col = varname_to_col[dkey]
        tooltip = """Enter an integer identifier based on the following:
          1 - Oral: slow release
          2 - Oral: immediate release
          3 - Intravenous"""
        self.pkdata_model.horizontalHeaderItem(dosetype_col).setToolTip(tooltip)

    def initializePage(self):
        sim_type = SimInfo.sim_type
        self._uses_pkdata = sim_type in self._sims_using_pkdata

        all_vars = PKDATA_FIELDS.keys()

        all_cols = self._vars_to_cols(all_vars)

        # start with all columns shown
        for c in all_cols:
            self.pkdata_table_view.showColumn(c)

        # for some sim types, certain columns are not relevant
        if self._uses_pkdata:
            page_title = "Dosing and Pharmacokinetic Data"
            data = SimInfo.pkdata
            # load current data
            self.write_dstruct_to_table(data, "pkdata")
        else:
            page_title = "Dosing"
            data = SimInfo.dosing
            vars_to_hide = [
                "subject_id",
                "trial_id",
                "body_mass",
                "sampling_times",
                "sampled_values",
            ]
            # load current data
            self.write_dstruct_to_table(data, "dosing")
            # we only need one row
            # TODO: Is it realistic to have multiple *different* dose types
            # in this context? That would necessitate more than one row.
            self.remove_rows(keep=1)
            cols_to_hide = self._vars_to_cols(vars_to_hide)
            for c in cols_to_hide:
                self.pkdata_table_view.hideColumn(c)

        # self.button_box.setVisible(self._uses_pkdata)
        # self.loadsave_box.setVisible(self._uses_pkdata)
        # self.edittable_box.setVisible(self._uses_pkdata)
        self.setTitle(page_title)
        self.pkdata_table_view.resizeColumnsToContents()

    def validatePage(self):
        # do some additional validation

        # ... and write values to the shared structure and db
        self.save_to_shared()
        self.save_to_db()
        return True

    def save_to_shared(self):
        container = io.StringIO()
        self.write_csv(container)
        data = container.getvalue()
        if self._uses_pkdata:
            section = "pkdata"
            data = self.write_table_into_dstruct(section)
            SimInfo.dosing = self._dosing = NULL_PKDATA_STRUCT
            SimInfo.pkdata = self._pkdata = data
        else:
            section = "dosing"
            data = self.write_table_into_dstruct(section)
            SimInfo.dosing = self._dosing = data
            SimInfo.pkdata = self._pkdata = NULL_PKDATA_STRUCT

    def _vars_to_cols(self, pkvars):
        cols = []
        for v in pkvars:
            label, col = PKDATA_FIELDS[v]
            cols.append(col)
        return set(cols)

    def save_to_db(self):
        db = SimInfo.db_info["database"]["db"]
        # save to mysims
        table_name = SimInfo.db_info["tables"]["mysims"]["name"]
        sim_id = SimInfo.sim_geninfo["sim_id"]
        update_map = {"dosing": self._dosing, "pkdata": self._pkdata}
        db_utils.update_record(db, table_name, sim_id, update_map)

    def add_dataset(self):
        self.load_blank_row()

    def load_blank_row(self):
        num_fields = len(self._pkdata_fields)
        row = [""] * num_fields
        items = [QStandardItem(field) for field in row]
        self.pkdata_model.appendRow(items)

    def remove_selected_row(self):
        idx = self.pkdata_table_view.currentIndex()
        self.pkdata_table_view.model().removeRow(idx.row())

    def import_datasets(self):
        fpath = None
        options = QFileDialog.Options() | QFileDialog.DontUseNativeDialog
        fpath, _ = QFileDialog.getOpenFileName(
            self, "Open data file", "", "PK Datasets (*.csv)", None, options=options
        )
        if fpath and isfile(fpath) and access(fpath, R_OK):
            with open(fpath, "r") as fh:
                self.load_data(fh)

    def remove_rows(self, keep=0):
        model = self.pkdata_model
        for row in range(model.rowCount() - keep):
            model.removeRow(0)

    def load_data(self, fh):
        # TODO: Add some validation here or in the 'import_datasets' method
        model = self.pkdata_model
        self.remove_rows()
        f_csv = csv.reader(fh)
        _ = next(f_csv)  # skip the header row
        for row in f_csv:
            items = [QStandardItem(field) for field in row]
            model.appendRow(items)

    def save_data(self):
        fpath = None
        options = QFileDialog.Options() | QFileDialog.DontUseNativeDialog
        fpath, _ = QFileDialog.getSaveFileName(
            self, "Save data", "", "PK Datasets (*.csv)", options=options
        )
        if fpath:
            with open(fpath, "w") as fh:
                self.write_csv(fh)

    def write_csv(self, fh):
        model = self.pkdata_model
        writer = csv.writer(fh)
        writer.writerow(self._pkdata_fields)
        for rowNumber in range(model.rowCount()):
            fields = [
                model.data(model.index(rowNumber, columnNumber), Qt.DisplayRole)
                for columnNumber in range(model.columnCount())
            ]
            writer.writerow(fields)

    def write_table_into_dstruct(self, section):
        container = io.StringIO()
        self.write_csv(container)
        data = container.getvalue().splitlines()
        without_header = data[1:]
        reader = csv.DictReader(without_header, fieldnames=self._pkdata_vars)
        dstruct = defaultdict(dict)
        sampled_variable = "C_central"
        for r in reader:
            if section == "pkdata":
                dstruct[r["subject_id"]][r["trial_id"]] = {
                    "body_mass": float(r["body_mass"]),
                    "dose_amounts": text_to_list(r["dose_amounts"]),
                    "dosing_times": text_to_list(r["dosing_times"]),
                    "dosing_type": r["dosing_type"],
                    "sampled_variable": sampled_variable,
                    "sampling_times": text_to_list(r["sampling_times"]),
                    "sampled_values": text_to_list(r["sampled_values"]),
                }
            elif section == "dosing":
                dstruct = {
                    "dosing_type": r["dosing_type"],
                    "dose_amounts": text_to_list(r["dose_amounts"]),
                    "dosing_times": text_to_list(r["dosing_times"]),
                }
            else:
                raise ValueError("Error: section must be 'pkdata' or 'dosing'")
        return dstruct

    def write_dstruct_to_table(self, dstruct, section):
        dlines = []
        header = ",".join(self._pkdata_fields)
        dlines.append(header)
        # create list of comma-separated lines
        if section == "pkdata":
            for subject_id, data in dstruct.items():
                for trial_id, vals in data.items():
                    line = [
                        subject_id,
                        trial_id,
                        vals["body_mass"],
                        vals["dosing_type"],
                        list_to_str(vals["dosing_times"]),
                        list_to_str(vals["dose_amounts"]),
                        list_to_str(vals["sampling_times"]),
                        list_to_str(vals["sampled_values"]),
                    ]
                    sline = ",".join([f'"{val}"' for val in line])
                    dlines.append(sline)
        elif section == "dosing":
            line = [
                "",  # subject_id
                "",  # trial_id
                "",  # body_mass
                dstruct["dosing_type"],
                list_to_str(dstruct["dosing_times"]),
                list_to_str(dstruct["dose_amounts"]),
                "",  # sampling_times
                "",  # sampled_values
            ]
            sline = ",".join([f'"{val}"' for val in line])
            dlines.append(sline)
        else:
            raise ValueError("Error: section must be 'pkdata' or 'dosing'")
        self.load_data(dlines)
