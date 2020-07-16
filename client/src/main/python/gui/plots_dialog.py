"""
.. module:: plots_dialog
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""


from PyQt5.QtWidgets import (
    QDialogButtonBox,
    QDialog,
    QPushButton,
    QVBoxLayout,
    QVBoxLayout,
    QWizardPage,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure

from utils import shared

SimInfo = shared.SimInfo()


class PlotsDialog(QDialog):
    def __init__(self, title, simplot, parent=None, *args):
        super().__init__(parent, *args)
        self._title = title
        self._plot = simplot
        self.setup_ui()

    def setup_ui(self):

        self.figure = Figure()
        self.canvas = FigureCanvas(self._plot)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        # set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setWindowTitle(f"Simulation results: {self._title}")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        self.show()


class NavigationToolbar(NavigationToolbar2QT):
    # only display the buttons we need
    toolitems = [
        t
        for t in NavigationToolbar2QT.toolitems
        if t[0] in ("Home", "Pan", "Zoom", "Save")
    ]
