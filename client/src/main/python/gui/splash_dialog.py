"""
.. module:: splash_dialog
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt


class SplashDialog(QSplashScreen):
    def __init__(self, appctxt, parent=None, *args):
        super().__init__(parent, *args)
        splash_pix = QPixmap(appctxt.splashscreen_image)
        splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
        splash.setMask(splash_pix.mask())
        splash.show()
