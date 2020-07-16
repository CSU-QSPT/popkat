"""
.. module:: settings
   :synopsis: Some configuration settings associated with MCSim/PoPKAT simulations

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""
import os
from pathlib import Path

import appdirs
import plotnine.themes
from rpyc.utils.classic import DEFAULT_SERVER_PORT as _DEFAULT_SERVER_PORT

from config.consts import APP_AUTHOR, APP_NAME

script_path = Path(os.path.dirname(os.path.realpath(__file__)))


def get_theme(x):
    return getattr(plotnine.themes, f"theme_{x}")


# ----------------------------------------------------------------------------
# user-customizable settings
# ----------------------------------------------------------------------------

# set the host and port
DEFAULT_HOST = "127.0.0.1"
DEFAULT_SERVER_PORT = _DEFAULT_SERVER_PORT

# Set the number of time points to use for kinetic simulations. This is used
# to set the time step since the start and end times are specified in the
# popkat file
NUM_TIME_PTS = 101

# Set the number of points to take from the end of the distribution for
# analysis. Counter-intuitively, a value of 0 means 'all points' because
# pts_for_analysis = all_pts[-lastn_pts:]
LASTN_PTS = 1000

# plot customization
# plotnine_themes: '538', 'bw', 'classic', 'dark', 'gray', 'light', 'linedraw',
#                  'matplotlib', 'minimal', 'seaborn', 'void', 'xkcd'
# select the theme
mytheme = "seaborn"
# ... but don't change this:
PLOT_THEME = get_theme(mytheme)

# set the plotting colors
# see http://colorbrewer2.org/ for some tasteful colors
MARKER_COLOR = "#1f77b4"  # matplotlib blue
LINE_COLOR = "#3d3d3d"  # gray 24
DASHED_LINE_COLOR = "#ff7f0e"  # matplotlib orange
BAR_COLOR = "#1f77b4"  # '#696969'    # dimgray

# set the base directory names on local and remote machines
LOCAL_BASE_DIR = "workspace"
REMOTE_BASE_DIR = "workspace"
MODELS_BASE_DIR = "models"

# select the sensitivity analysis method
# see `consts.SA_LIB_METHODS` for the choice of methods
# Details about SALib are given at https://salib.readthedocs.io/en/latest/api.html
SA_METHOD = "sobol"

# set the name of the sub-directory used for backups
BACKUP_DIR_NAME = "backups"

# set the subdirectory name to sore files referred to in the database
SIM_DB_ASSOC_FILE_DIR = ".simulations_storage"
SAMP_DB_ASSOC_FILE_DIR = ".samples_storage"

# set the number of backups of the database to keep
NUM_BACKUPS_TO_KEEP = 4

# Set the compression type for stored files (bz2, zip, lzma)
COMPRESSION_TYPE = "bz2"

# settings for mcmc and sens analyses
MODEL_PARAM_SENSITIVITY = {"low_factor": 10, "high_factor": 10}
MODEL_PARAM_VARIABILITY = {"cv_ind": 0.5, "cv_pop": 3}
SIM_SOLVER_TOLERANCES = {"rtol": 0.000001, "atol": 0.000001}

# database information
# TODO: change DB_DATA_DIR to actual installed location
DB_DATA_DIR = Path(appdirs.user_data_dir(APP_NAME, APP_AUTHOR), "data")
DB_PATH = str(DB_DATA_DIR / "simulations.pkt")
# alias: table name in database
DB_TABLE_NAMES = {"mysims": "mysims", "samples": "samples"}
