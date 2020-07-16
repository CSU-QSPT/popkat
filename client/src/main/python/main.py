"""
.. module:: __main__
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""


import sys
import time

from fbs_runtime.application_context.PyQt5 import ApplicationContext, cached_property
from PyQt5.QtWidgets import QApplication

from gui import main_page, splash_dialog

splash_duration = 1  # seconds


class AppContext(ApplicationContext):
    def run(self):
        return self.app.exec_()

    @cached_property
    def splashscreen_image(self):
        # the image to be used in the splashscreen
        return self.get_resource("images/popkat_logo.png")


# --------------------------------------------------------------------------------------


def main():
    appctxt = AppContext()
    app = QApplication(sys.argv)
    splash = splash_dialog.SplashDialog(appctxt)
    app.processEvents()
    time.sleep(splash_duration)
    wizard = main_page.Wizard()
    splash.finish(wizard)
    wizard.show()
    # wizard.showMaximized()
    exit_code = appctxt.run()
    sys.exit(exit_code)


# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
