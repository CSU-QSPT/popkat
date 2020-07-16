"""
.. module:: server
   :synopsis: Threaded server based on rpyc

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import argparse
import logging
import appdirs
import os

from rpyc.core import SlaveService
from rpyc.utils.server import ThreadedServer

from server_config import (
    DEFAULT_HOST,
    DEFAULT_LOG_LEVEL,
    DEFAULT_SERVER_LOGFILE,
    DEFAULT_SERVER_PORT,
    APP_SERVER_NAME,
    APP_AUTHOR,
)

# Constant to set allowable choices for the logging value
LOGGING_LEVELS = sorted(
    [
        logging.CRITICAL,
        logging.ERROR,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
        logging.NOTSET,
    ]
)


class SimServer(object):
    """Threaded server based on rpyc"""

    def __init__(
        self,
        app_name=APP_SERVER_NAME,
        app_author=APP_AUTHOR,
        host=DEFAULT_HOST,
        port=DEFAULT_SERVER_PORT,
        logfile=DEFAULT_SERVER_LOGFILE,
        loglevel=DEFAULT_LOG_LEVEL,
    ):
        logdir = self._create_logdir(app_name, app_author)
        self.host = host
        self.port = port
        self.logfile = os.path.join(logdir, logfile)
        self.loglevel = loglevel

    def _create_logdir(self, app_name, app_author):
        """Create the log directory"""
        user_log_dir = appdirs.user_log_dir(app_name, app_author)
        os.makedirs(user_log_dir, exist_ok=True)
        return user_log_dir

    def start(self):
        """Start the threaded server"""
        logging.basicConfig(
            format="%(asctime)s | %(levelname)s | %(message)s",
            level=self.loglevel,
            filename=self.logfile,
        )
        conn = ThreadedServer(
            SlaveService, hostname=self.host, port=self.port, reuse_addr=True
        )
        conn.start()


def start_server(
    app_name=APP_SERVER_NAME,
    app_author=APP_AUTHOR,
    host=DEFAULT_HOST,
    port=DEFAULT_SERVER_PORT,
    logfile=DEFAULT_SERVER_LOGFILE,
    loglevel=DEFAULT_LOG_LEVEL,
):
    pksrv = SimServer(
        app_name=app_name,
        app_author=app_author,
        host=host,
        port=port,
        logfile=logfile,
        loglevel=loglevel,
    )
    pksrv.start()


# ------------------------------------------------------------------------------

def main():

    def ip_address_type(ip_):
        okay = True
        ip_ = ip_.strip()
        if ip_ != "localhost":
            groups = [int(x) for x in ip_.split(".")]
            okay = (len(groups) == 4) and all([0 <= g <= 255 for g in groups])
        if not okay:
            raise argparse.ArgumentTypeError(f"{ip_} is not a valid ip address")
        return ip_

    def port_type(port_):
        port_ = int(port_)
        if port_ < 0 or port_ > 2 ** 16 - 1:
            raise argparse.ArgumentTypeError(f"{port_} is not a valid port number")
        else:
            return port_

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--app_name",
        dest="app_name",
        action="store",
        type=str,
        default=APP_SERVER_NAME,
        help="The name of the server application",
    )
    parser.add_argument(
        "--app_author",
        dest="app_author",
        action="store",
        type=str,
        default=APP_AUTHOR,
        help="The author of the application",
    )
    parser.add_argument(
        "--port",
        dest="port",
        action="store",
        type=port_type,
        default=DEFAULT_SERVER_PORT,
        help=f"The TCP listener port",
    )
    parser.add_argument(
        "--host",
        dest="host",
        action="store",
        type=ip_address_type,
        default=DEFAULT_HOST,
        help="The host to bind to",
    )
    parser.add_argument(
        "--logfile",
        dest="logfile",
        action="store",
        type=str,
        default=DEFAULT_SERVER_LOGFILE,
        help="The log file to use",
    )
    parser.add_argument(
        "--loglevel",
        dest="loglevel",
        action="store",
        type=int,
        choices=LOGGING_LEVELS,
        default=DEFAULT_LOG_LEVEL,
        help="The log level to use",
    )
    args = parser.parse_args()
    start_server(
        host=args.host, port=args.port, logfile=args.logfile, loglevel=args.loglevel
    )

#---------------------------------------------------------------------------------------

if __name__ == "__main__":
    main()
