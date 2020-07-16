"""
.. module:: server_config
   :synopsis: Some configuration settings associated with MCSim/PoPKAT simulations

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import logging

from rpyc.utils.classic import DEFAULT_SERVER_PORT as _DEFAULT_SERVER_PORT

DEFAULT_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = _DEFAULT_SERVER_PORT
DEFAULT_LOG_LEVEL = logging.DEBUG
DEFAULT_SERVER_LOGFILE = "popkat_server.log"

# Values used for directory creation
# These values *MUST* be the same as those in 'consts.py'
APP_NAME = "popkat"
APP_SERVER_NAME = "popkat_server"
APP_AUTHOR = "qspt"
