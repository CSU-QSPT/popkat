"""
.. module:: main
   :synopsis: Main module for PoPKAT GUI

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from PyQt5.QtWidgets import QWizard
from PyQt5.QtCore import QCoreApplication, QSettings, Qt

from simselect_page import SimSelectPage
from siminfo_page import SimInfoPage
from modelparams_page import ModelParamsPage
from dosingpkdata_page import DosingPKDataPage
from simrun_page import SimRunPage
from simresults_page import SimResultsPage

from page_info import PageID, HELP_FILES
from help_dialog import HelpDialog
from utils import shared, db_utils
from config.settings import DB_PATH, DB_TABLE_NAMES
from config.consts import APP_NAME, APP_AUTHOR
from execute import localserver

SimInfo = shared.SimInfo()


class Wizard(QWizard):
    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)
        self._init_databases()
        self.read_settings()
        self.setup_ui()
        self.start_simserver(self)

    def start_simserver(self, parent=None):
        """This runs the server via a QThread so that the GUI doesn't
        block"""
        localserver.start_server(parent)

    def read_settings(self):
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QCoreApplication.setOrganizationName(APP_AUTHOR)
        QCoreApplication.setApplicationName(APP_NAME)
        self.settings = QSettings()

    def setup_ui(self):
        self.setPage(PageID.SIM_SELECT_PAGE.value, SimSelectPage(self))
        self.setPage(PageID.SIM_INFO_PAGE.value, SimInfoPage(self))
        self.setPage(PageID.MODEL_PARAMS_PAGE.value, ModelParamsPage(self))
        self.setPage(PageID.DOSING_PKDATA_PAGE.value, DosingPKDataPage(self))
        self.setPage(PageID.SIM_RUN_PAGE.value, SimRunPage(self))
        self.setPage(PageID.SIM_RESULTS_PAGE.value, SimResultsPage(self))

        self.setWindowTitle("PoPKAT")
        self.setWizardStyle(self.ModernStyle)
        self.setOption(self.HaveHelpButton, True)

        # set shortcuts for Next and Back buttons
        QWizard.button(self, QWizard.NextButton).setShortcut("Alt+N")
        QWizard.button(self, QWizard.BackButton).setShortcut("Alt+B")

        # the finish button
        self.button(QWizard.FinishButton).clicked.connect(self._onClose)

        # set up help messages
        self.helpRequested.connect(self._showHelp)

        # self.showMaximized()
        self.setWindowFlags(
            Qt.Window
            | Qt.CustomizeWindowHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        self.resize(1024, 768)

    def _init_databases(self):
        SimInfo.db_info = (DB_PATH, DB_TABLE_NAMES)

    def _clean_database(self):
        db = SimInfo.db_info["database"]["db"]
        for table_info in SimInfo.db_info["tables"].values():
            table = table_info["name"]
            db_utils.delete_duplicate_rows(db, table)

    def _showHelp(self):
        # get the help message for the current page
        file_path = HELP_FILES[self.currentId()]
        help_page = HelpDialog(file_path, parent=self)
        help_page.show()

    def closeEvent(self, event):
        self._onClose()
        event.accept()

    def _onClose(self):
        # do some db-related activities
        self._clean_database()  # remove (essentially) duplicate rows
        db_utils.backup_db_file()
        # store settings?
        # this is not working yet
        self.settings.setValue("size", self.size())
        self.settings.setValue("position", self.pos())
