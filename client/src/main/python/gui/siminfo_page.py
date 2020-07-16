"""
.. module:: siminfo_page
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from functools import partial

from PyQt5.QtWidgets import (
    QLineEdit,
    QWizardPage,
    QVBoxLayout,
    QGroupBox,
    QLabel,
    QGridLayout,
    QRadioButton,
    QFormLayout,
    QButtonGroup,
)
from PyQt5.QtCore import Qt

from utils import shared
from utils import db_utils

from config.consts import SIM_TYPES_INFO
from config.settings import SIM_SOLVER_TOLERANCES

SimInfo = shared.SimInfo()


class SimInfoPage(QWizardPage):
    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)
        self.setup_ui()

    def initializePage(self):
        self._sim_geninfo = SimInfo.sim_geninfo
        self._sim_params = SimInfo.sim_params
        sim_type = SimInfo.sim_type
        self.simtype_to_button[sim_type].click()
        # fill in the general information
        for d, val in self.geninfo_ledit.items():
            val["widget"].setText(self._sim_geninfo[d])
        # fill in the sim params
        for var_name, widget in self.sim_type_details_widgets.items():
            widget.setText(str(self._sim_params[var_name]))

    def validatePage(self):
        # do some additional validation

        # ... and write values to the shared structure and db
        self.save_to_shared()
        self.save_to_db()
        return True

    def save_to_shared(self):
        SimInfo.sim_params = {**self._sim_params, **SIM_SOLVER_TOLERANCES}
        SimInfo.sim_geninfo = self._sim_geninfo

    def save_to_db(self):
        db = SimInfo.db_info["database"]["db"]
        # save to mysims
        table_name = SimInfo.db_info["tables"]["mysims"]["name"]
        sim_id = self._sim_geninfo["sim_id"]
        update_map = {
            "description": self._sim_geninfo["description"],
            "notes": self._sim_geninfo["notes"],
            "tags": self._sim_geninfo["tags"],
            "sim_params": self._sim_params,
            "sim_type": self._sim_params["sim_type"],
        }
        db_utils.update_record(db, table_name, sim_id, update_map)

    def setup_ui(self):

        page_layout = QGridLayout()

        # ----------------------------------------------------------------------
        # gen sim info
        # ----------------------------------------------------------------------
        self.geninfo_box = QGroupBox("General information")
        self.geninfo_layout = QGridLayout()
        self.geninfo_box.setLayout(self.geninfo_layout)
        self.new_sim_id = None
        # label, data_key, can_be_empty, tooltip
        self.fields = [
            ("Description:", "description", False, None),
            ("Notes:", "notes", True, None),
            ("Tags", "tags", True, "Space- or comma-separated list of values"),
        ]

        self.geninfo_ledit = {}
        for row, (label, data_key, can_be_empty, tooltip) in enumerate(self.fields):
            lbl = QLabel(label)
            ledit = QLineEdit()
            if tooltip:
                lbl.setToolTip(tooltip)
            self.geninfo_layout.addWidget(lbl, row, 0)
            self.geninfo_layout.addWidget(ledit, row, 1)
            self.geninfo_ledit[data_key] = {
                "widget": ledit,
                "validation_info": can_be_empty,
            }
            ledit.editingFinished.connect(
                partial(self.onEditedGenInfo, data_key, ledit)
            )

        self.geninfo_box.setLayout(self.geninfo_layout)

        # ----------------------------------------------------------------------
        # Sim type selection
        # ----------------------------------------------------------------------
        simtype_box = QGroupBox("Simulation type")
        simtype_layout = QVBoxLayout()
        self.simtype_choices = QButtonGroup()
        self.simtype_choices.setExclusive(True)
        simtype_box.setLayout(simtype_layout)

        simdetails_box = QGroupBox("Simulation details")
        simdetails_layout = QFormLayout()
        simdetails_box.setLayout(simdetails_layout)
        # simdetails_layout.setLabelAlignment(Qt.AlignLeft)
        simdetails_layout.setFormAlignment(Qt.AlignLeft)

        self.ind_to_simtype = {}
        self.simtype_to_button = {}
        for ind, (stype, val) in enumerate(SIM_TYPES_INFO.items()):
            self.ind_to_simtype[ind] = stype
            rbtn = QRadioButton(val["full_name"])
            rbtn.setProperty("name", stype)
            self.simtype_choices.addButton(rbtn)
            self.simtype_choices.setId(rbtn, ind)
            self.simtype_to_button[stype] = rbtn
            simtype_layout.addWidget(rbtn)

        self.simtype_choices.buttonClicked.connect(
            partial(self.onRadioClicked, simdetails_layout)
        )

        # ----------------------------------------------------------------------
        # Overall form
        # ----------------------------------------------------------------------
        page_layout.addWidget(self.geninfo_box, 0, 0, 1, 2)
        page_layout.addWidget(simtype_box, 1, 0)
        page_layout.addWidget(simdetails_box, 1, 1)

        self.setLayout(page_layout)
        self.setTitle("Simulation Information")

    def update_sim_type_details(self, layout, sim_type):
        self.clear_layout(layout)
        self.sim_type_details_widgets = {}
        fields = SIM_TYPES_INFO[sim_type]["analysis_details"]

        # update the details area
        for var_name, text in fields:
            flabel = QLabel(text)
            tedit = QLineEdit()
            tedit.editingFinished.connect(
                partial(self.onEditedSimParams, var_name, tedit)
            )
            layout.addRow(flabel, tedit)
            self.sim_type_details_widgets[var_name] = tedit

    def onEditedGenInfo(self, key, widget):
        val = widget.text()
        self._sim_geninfo[key] = val

    def onEditedSimParams(self, key, widget):
        val = widget.text()
        self._sim_params[key] = val

    def clear_layout(self, layout):
        for irow in reversed(range(layout.count())):
            layout.itemAt(irow).widget().setParent(None)

    def onRadioClicked(self, layout):
        checked_id = self.simtype_choices.checkedId()
        sim_type = self.ind_to_simtype[checked_id]
        self.update_sim_type_details(layout, sim_type)
        self._sim_params["sim_type"] = sim_type
