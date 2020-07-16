"""
.. module:: localserver
   :synopsis: The application server for PoPKAT

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from PyQt5.QtCore import QThread

from popkat_server.server_config import (
    DEFAULT_HOST,
    DEFAULT_SERVER_PORT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_SERVER_LOGFILE,
    APP_SERVER_NAME,
    APP_AUTHOR,
)
from utils import gen_utils
from popkat_server import server


class ServerThread(QThread):
    def __init__(
        self,
        parent=None,
        app_name=APP_SERVER_NAME,
        app_author=APP_AUTHOR,
        host=DEFAULT_HOST,
        port=DEFAULT_SERVER_PORT,
        logfile=DEFAULT_SERVER_LOGFILE,
        loglevel=DEFAULT_LOG_LEVEL,
    ):
        super().__init__(parent)
        self.app_name = app_name
        self.app_author = app_author
        self.host = host
        self.port = port
        self.logfile = logfile
        self.loglevel = loglevel

    def run(self):
        server.start_server(
            app_name=self.app_name,
            app_author=self.app_author,
            host=self.host,
            port=self.port,
            logfile=self.logfile,
            loglevel=self.loglevel,
        )


def start_server(
    parent=None,
    app_name=APP_SERVER_NAME,
    app_author=APP_AUTHOR,
    host=DEFAULT_HOST,
    port=DEFAULT_SERVER_PORT,
    logfile=DEFAULT_SERVER_LOGFILE,
    loglevel=DEFAULT_LOG_LEVEL,
):
    """Start a local server
    Only run this if the host represents the local machine"""
    if gen_utils.is_localhost(host):
        sthread = ServerThread(
            parent=parent,
            app_name=app_name,
            app_author=app_author,
            host=host,
            port=port,
            logfile=logfile,
            loglevel=loglevel,
        )
        sthread.start()
