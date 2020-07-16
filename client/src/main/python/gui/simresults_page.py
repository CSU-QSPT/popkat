"""
.. module:: simresults_page
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from functools import partial

from PyQt5.QtWidgets import (
    QWizardPage,
    QHBoxLayout,
    QVBoxLayout,
    QGroupBox,
    QPushButton,
    QAbstractButton,
)
from PyQt5.QtGui import QPainter

from plots_dialog import PlotsDialog
from tables_dialog import TablesDialog

from utils import shared

SimInfo = shared.SimInfo()


class SimResultsPage(QWizardPage):
    def __init__(self, parent=None, *args):
        super().__init__(parent, *args)
        self.setup_ui()

    def initializePage(self):
        # clear the layout, otherwise we keep appending new widgets every
        # time we visit the page
        self.clear_layout(self.plot_layout)
        self.clear_layout(self.table_layout)

        output_plots = SimInfo.output_plots
        output_tables = SimInfo.output_tables
        for title, figure in output_plots.items():
            pbtn = QPushButton(title)
            pbtn.clicked.connect(partial(self.on_click_plot, title, figure))
            pbtn.setToolTip(title)
            self.plot_layout.addWidget(pbtn)

        for title, table in output_tables.items():
            tbtn = QPushButton(title)
            tbtn.clicked.connect(partial(self.on_click_table, title, table))
            tbtn.setToolTip(title)
            self.table_layout.addWidget(tbtn)

    def clear_layout(self, layout):
        for irow in reversed(range(layout.count())):
            layout.itemAt(irow).widget().setParent(None)

    def on_click_plot(self, title, figure):
        plot = PlotsDialog(title, figure, parent=None)

    def on_click_table(self, title, table):
        table = TablesDialog(title, table, parent=self)

    def setup_ui(self):
        self.setTitle("Simulation Results")

        page_layout = QHBoxLayout()

        # ----------------------------------------------------------------------
        # plots
        # ----------------------------------------------------------------------
        plot_box = QGroupBox("Plots")
        self.plot_layout = QVBoxLayout()
        plot_box.setLayout(self.plot_layout)

        # ----------------------------------------------------------------------
        # tables
        # ----------------------------------------------------------------------
        table_box = QGroupBox("Tables")
        self.table_layout = QVBoxLayout()
        table_box.setLayout(self.table_layout)

        # ----------------------------------------------------------------------
        # page
        # ----------------------------------------------------------------------
        page_layout.addWidget(plot_box)
        page_layout.addWidget(table_box)
        self.setLayout(page_layout)


class PicButton(QAbstractButton):
    def __init__(self, pixmap, parent=None):
        super(PicButton, self).__init__(parent)
        self.pixmap = pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(event.rect(), self.pixmap)

    def sizeHint(self):
        return self.pixmap.size()
