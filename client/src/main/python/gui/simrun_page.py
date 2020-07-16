"""
.. module:: run_sim
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from collections import defaultdict
import pickle

from PyQt5.QtWidgets import (
    QWizard,
    QProgressBar,
    QGridLayout,
    QWizardPage,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QGroupBox,
    QTextEdit,
    QPushButton,
)

# from PyQt5.QtCore import pyqtSignal, pyqtSlot, QTimer

from execute import workflows
from utils import shared, db_utils
from config.consts import MsgDest


SimInfo = shared.SimInfo()


class SimRunPage(QWizardPage):
    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)
        self._sim_complete = False
        self._parent = parent
        self.setup_ui()

    def initializePage(self):
        self._sim_specs = SimInfo.sim_specs
        self._model_label = SimInfo.sim_geninfo["model_label"]
        self.sim_id = SimInfo.sim_geninfo["sim_id"]
        _info = dict(**SimInfo.sim_geninfo, **SimInfo.sim_params)
        for desc, key, lbl in self.info_labels:
            text = f"{desc}: {_info[key]}"
            lbl.setText(text)

    def isComplete(self):
        complete = self._sim_complete
        return complete

    def setup_ui(self):
        SimInfo.meta_info = defaultdict(dict)
        self.info_keys = [
            ("Description", "description"),
            ("Notes", "notes"),
            ("Tags", "tags"),
            ("Model name", "model_label"),
            ("Sim type", "sim_type"),
        ]

        page_layout = QGridLayout(self)

        # ----------------------------------------------------------------------
        # information
        # ----------------------------------------------------------------------
        self.info_layout = QVBoxLayout()
        info_group = QGroupBox("Simulation information")
        info_group.setLayout(self.info_layout)
        self.info_labels = []
        for desc, key in self.info_keys:
            text = f"{desc}:"
            lbl = QLabel(text)
            self.info_layout.addWidget(lbl)
            self.info_labels.append((desc, key, lbl))

        # ----------------------------------------------------------------------
        # status
        # ----------------------------------------------------------------------
        status_window = QTextEdit()
        status_window.setLineWrapMode(QTextEdit.FixedPixelWidth)
        status_layout = QVBoxLayout()
        status_group = QGroupBox("Simulation messages and status")
        status_group.setLayout(status_layout)
        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)

        status_layout.addWidget(status_window)
        status_layout.addWidget(progress_bar)

        # ----------------------------------------------------------------------
        # actions
        # ----------------------------------------------------------------------
        actions_layout = QHBoxLayout()
        actions_group = QGroupBox("Simulation actions")
        actions_group.setLayout(actions_layout)
        start_sim = QPushButton("Start simulation")
        start_sim.clicked.connect(self.on_click_start)
        stop_sim = QPushButton("Stop simulation")
        stop_sim.clicked.connect(self.on_click_stop)
        actions_layout.addWidget(start_sim)
        actions_layout.addWidget(stop_sim)

        page_layout.addWidget(info_group, 0, 0, 1, 2)
        page_layout.addWidget(status_group, 1, 0, 1, 2)
        page_layout.addWidget(actions_group, 2, 1)

        self.setLayout(page_layout)
        self.setTitle("Run and Monitor Simulation")

    def run_sim(self, iter_freq=1, do_cleanup=True, storage_path=None):
        self.results = workflows.run_workflow(
            self._sim_specs,
            self._model_name,
            msg_dest=MsgDest.SOCKET,
            do_cleanup=do_cleanup,
            iter_freq=iter_freq,
            storage_path=storage_path,
        )
        self.is_sim_complete(self.results)

    def is_sim_complete(self, results):
        self._sim_complete = any(results.values())
        self._parent.button(QWizard.BackButton).setEnabled(True)
        self.completeChanged.emit()

    def save_to_shared(self):
        SimInfo.output_plots = self._output_plots = self.results["plots"]
        SimInfo.output_tables = self._output_tables = self.results["tables"]

    def save_to_db(self):
        db = SimInfo.db_info["database"]["db"]
        # save to mysims
        table_name = SimInfo.db_info["tables"]["mysims"]["name"]
        update_map = {
            "output_plots": pickle.dumps(self._output_plots),
            "output_tables": pickle.dumps(self._output_tables),
        }
        db_utils.update_record(db, table_name, self.sim_id, update_map)

    def validatePage(self):
        # do some additional validation

        # ... and write values to the shared structure
        self.save_to_shared()
        self.save_to_db()
        return True

    def on_click_start(self):
        self._parent.button(QWizard.BackButton).setEnabled(False)
        self.run_sim()
        self.store_results()
        print("Start simulation")

    def on_click_stop(self):
        print("Stop simulation")

    def enable_buttons(self):
        pass
