"""
.. module:: selectsim_page
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import pickle

from PyQt5.QtCore import QSortFilterProxyModel, Qt
from PyQt5.QtWidgets import (
    QTreeView,
    QLineEdit,
    QWizardPage,
    QGroupBox,
    QLabel,
    QGridLayout,
    QAbstractItemView,
    QMenu,
    QMessageBox,
)


from utils import shared
from utils import gen_utils
from utils import gui_utils
from utils import db_utils

SimInfo = shared.SimInfo()


class SimSelectPage(QWizardPage):
    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)
        self.setup_ui()
        self._storage_info = None
        self._table_with_focus = None

    def initializePage(self):
        pass

    def validatePage(self):
        # do some additional validation
        # TODO: confirm that the check for self._storage_info is appropriate

        if self._storage_info is None:
            msg = (
                "Please select a simulation by clicking on an item in one of the "
                "'simulation' tables."
            )
            title = "Error: No simulation selected"
            self.error_message(msg, title)
            return False
        # ... and write values to the shared structure
        self.save_to_shared()
        self.save_to_db()
        return True

    def error_message(self, message, title):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle(title)
        rval = msg.exec()
        if rval == QMessageBox.Ok:
            self.sim_view.setFocus()

    def setup_ui(self):
        # ----------------------------------------------------------------------
        # Database section
        # ----------------------------------------------------------------------
        table_grid = QGridLayout()
        table_group_box = QGroupBox()

        self.sim_model = SimInfo.db_info["tables"]["mysims"]["model"]
        self.sample_model = SimInfo.db_info["tables"]["samples"]["model"]
        col_map = SimInfo.db_info["col_map"]

        # ----------------------------------------------------------------------
        # Database table views section
        # ----------------------------------------------------------------------
        self.sim_view = QTreeView()
        self.sim_view.setAlternatingRowColors(True)
        self.sim_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sim_view.setModel(self.sim_model)
        self.sim_view.setSortingEnabled(True)
        self.create_context_menu()
        self.sim_view.customContextMenuRequested.connect(self.on_context_menu)

        self.sample_view = QTreeView()
        self.sample_view.setAlternatingRowColors(True)
        self.sample_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sample_view.setModel(self.sample_model)
        self.sample_view.setSortingEnabled(True)
        self.sim_view.setContextMenuPolicy(Qt.CustomContextMenu)

        # header = self.sim_view.horizontalHeader()
        self.sim_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sim_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sample_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sample_view.setSelectionBehavior(QAbstractItemView.SelectRows)

        to_hide = [
            "key",
            "sim_id",
            "other_info",
            "sim_params",
            "model_params",
            "pkdata",
            "dosing",
            "input_files",
            "env_file",
            "model_exe",
            "output_files",
            "output_plots",
            "output_tables",
        ]
        for col in [col_map[name] for name in to_hide]:
            self.sim_view.hideColumn(col)
            self.sample_view.hideColumn(col)

        sim_label = QLabel("My simulations")
        sample_label = QLabel("Sample simulations")

        table_grid.addWidget(sim_label, 0, 0)
        table_grid.addWidget(self.sim_view, 1, 0)
        table_grid.addWidget(sample_label, 0, 1)
        table_grid.addWidget(self.sample_view, 1, 1)

        table_group_box.setLayout(table_grid)

        # ----------------------------------------------------------------------
        # Selection section
        # ----------------------------------------------------------------------
        data_grid = QGridLayout()
        selection_group_box = QGroupBox("Simulation details")

        self.description = QLabel()
        self.notes = QLabel()
        self.tags = QLabel()
        self.sim_timestamp = QLabel()
        self.model_label = QLabel()
        self.sim_type = QLabel()

        data_grid.addWidget(self.description, 0, 0)
        data_grid.addWidget(self.notes, 1, 0)
        data_grid.addWidget(self.tags, 2, 0)
        data_grid.addWidget(self.model_label, 3, 0)
        data_grid.addWidget(self.sim_type, 4, 0)
        data_grid.addWidget(self.sim_timestamp, 5, 0)

        selection_group_box.setLayout(data_grid)

        # ----------------------------------------------------------------------
        # Search section
        # ----------------------------------------------------------------------
        search_grid = QGridLayout()
        search_group_box = QGroupBox("Search simulations")

        search_label = QLabel("Search term")
        search_text = QLineEdit()

        search_grid.addWidget(search_label, 0, 0)
        search_grid.addWidget(search_text, 0, 1)

        search_group_box.setLayout(search_grid)
        # the columns that will be searched
        cols_to_search = ["notes", "description", "tags", "timestamp", "model_label"]
        fcols = [col_map[col] for col in cols_to_search]

        self.sim_filter_proxy_model = QfTreeProxyModel(self, fcols)
        self.sim_filter_proxy_model.setSourceModel(self.sim_model)
        self.sim_view.setModel(self.sim_filter_proxy_model)
        self.sim_filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.sample_filter_proxy_model = QfTreeProxyModel(self, fcols)
        self.sample_filter_proxy_model.setSourceModel(self.sample_model)
        self.sample_view.setModel(self.sample_filter_proxy_model)
        self.sample_filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        search_text.textChanged.connect(self.sim_filter_proxy_model.setFilterRegExp)
        search_text.textChanged.connect(self.sample_filter_proxy_model.setFilterRegExp)
        self.sim_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sample_view.setSelectionBehavior(QAbstractItemView.SelectRows)

        # ----------------------------------------------------------------------
        # Overall form
        # ----------------------------------------------------------------------
        form_layout = QGridLayout()
        form_layout.addWidget(table_group_box, 0, 0, 1, 2)
        form_layout.addWidget(selection_group_box, 2, 0)
        form_layout.addWidget(search_group_box, 1, 0)

        self.setLayout(form_layout)
        self.setTitle("Simulation Selection")
        self.show()
        self.sim_view.clicked.connect(self.on_focus_sim)
        self.sample_view.clicked.connect(self.on_focus_sample)
        self.sim_view.selectionModel().selectionChanged.connect(self.on_focus_sim)
        self.sample_view.selectionModel().selectionChanged.connect(self.on_focus_sample)

    def create_context_menu(self, parent=None):
        self.context_menu = QMenu(parent)
        self.context_menu.addAction("Delete simulation", self._delete_sim)

    def on_context_menu(self, pos):
        self.context_menu.exec_(self.sim_view.mapToGlobal(pos))

    def _delete_sim(self):
        idx = self.sim_view.currentIndex()
        record = self.sim_model.record(
            self.sim_filter_proxy_model.mapToSource(idx).row()
        )
        description = record.field("description").value()
        reply = QMessageBox.question(
            self,
            "Confirm simulation deletion",
            (
                "Are you sure you want to delete the simulation with description "
                f"'{description}'?"
            ),
            QMessageBox.Yes,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.sim_view.model().beginRemoveRows(idx.parent(), idx.row(), idx.row())
            self.sim_view.model().removeRow(idx.row(), idx.parent())
            self.sim_view.model().endRemoveRows()
            self.sim_model.select()

    def on_focus_sim(self):
        index = self.sim_view.currentIndex()
        record = self.sim_model.record(
            self.sim_filter_proxy_model.mapToSource(index).row()
        )
        self.sample_view.clearSelection()
        self.set_selected_text(record)
        self._table_with_focus = "mysims"

    def on_focus_sample(self):
        index = self.sample_view.currentIndex()
        record = self.sample_model.record(
            self.sample_filter_proxy_model.mapToSource(index).row()
        )
        self.sim_view.clearSelection()
        self.set_selected_text(record)
        self._table_with_focus = "samples"

    def set_selected_text(self, record):
        self._record = record
        # generate new sim_id, even if the user hasn't changed anything
        # also generate a new timestamp
        new_sim_id = gui_utils.generate_sim_id()
        new_timestamp = gen_utils.timestamp()

        description = record.field("description").value()
        notes = record.field("notes").value()
        timestamp = record.field("timestamp").value()
        tags = record.field("tags").value()
        sim_type = record.field("sim_type").value()
        sim_id = record.field("sim_id").value()
        model_label = record.field("model_label").value()

        self.description.setText(f"Description: {description}")
        self.notes.setText(f"Notes: {notes}")
        self.sim_timestamp.setText(f"Timestamp: {new_timestamp}")
        self.tags.setText(f"Tags: {tags}")
        self.model_label.setText(f"Model name: {model_label}")
        self.sim_type.setText(f"Simulation type: {sim_type}")

        sim_params = pickle.loads(record.field("sim_params").value())
        model_params = pickle.loads(record.field("model_params").value())
        dosing = pickle.loads(record.field("dosing").value())
        pkdata = pickle.loads(record.field("pkdata").value())
        output_plots = pickle.loads(record.field("output_plots").value())
        output_tables = pickle.loads(record.field("output_tables").value())
        sim_geninfo = {
            "description": description,
            "notes": notes,
            "tags": tags,
            "sim_id": new_sim_id,
            "timestamp": new_timestamp,
            "model_label": model_label,
        }
        simfile_list = ["input_files", "env_file", "model_exe", "output_files"]
        sim_files = {sf: record.field(sf).value() for sf in simfile_list}
        self._storage_info = {
            "sim_type": sim_type,
            "model_label": model_label,
            "sim_id": sim_id,
            "new_sim_id": new_sim_id,
            "timestamp": timestamp,
            "new_timestamp": new_timestamp,
            "sim_params": sim_params,
            "model_params": model_params,
            "dosing": dosing,
            "pkdata": pkdata,
            "output_plots": output_plots,
            "output_tables": output_tables,
            "sim_geninfo": sim_geninfo,
            "sim_files": sim_files,
        }

    def save_to_shared(self):
        plist = [
            "sim_params",
            "model_params",
            "dosing",
            "pkdata",
            "sim_type",
            "model_label",
            "output_plots",
            "output_tables",
            "sim_geninfo",
            "sim_files",
        ]
        for p in plist:
            setattr(SimInfo, p, self._storage_info[p])

    def save_to_db(self):
        sim_id = self._storage_info["sim_id"]
        new_sim_id = self._storage_info["new_sim_id"]
        timestamp = self._storage_info["timestamp"]
        new_timestamp = self._storage_info["new_timestamp"]

        db = SimInfo.db_info["database"]["db"]
        dest_table = SimInfo.db_info["tables"]["mysims"]["name"]

        # copy within the mysims table or between tables (samples -> mysims)
        if self._table_with_focus == "mysims":
            src_table = dest_table
        if self._table_with_focus == "samples":
            src_table = SimInfo.db_info["tables"]["samples"]["name"]
        db_utils.copy_record(
            db, src_table, dest_table, sim_id, new_sim_id, timestamp, new_timestamp
        )


class QfTreeProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None, fcols=None):
        super().__init__(parent)
        self._fcols = fcols
        if fcols is None:
            fcols = [self.filterKeyColumn]

    def filterAcceptsRow(self, sourceRow, sourceParent):
        model = self.sourceModel()
        cols = self._fcols
        was_found = []
        for c in cols:
            index = model.index(sourceRow, c, sourceParent)
            data = model.data(index)
            found = self.filterRegExp().indexIn(data) != -1
            was_found.append(found)
        return any(was_found)
