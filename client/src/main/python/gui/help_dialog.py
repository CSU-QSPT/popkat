"""
.. module:: help_utils
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""


from PyQt5.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl


class HelpDialog(QDialog):
    def __init__(self, file_path, parent=None, *args):
        super().__init__(parent, *args)
        self.setup_ui(file_path)

    def setup_ui(self, file_path):
        layout = QVBoxLayout(self)
        help_viewer = QWebEngineView()
        local_url = QUrl.fromLocalFile(str(file_path))
        help_viewer.load(local_url)
        layout.addWidget(help_viewer)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.setWindowTitle("PoPKAT help")
