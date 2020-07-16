"""
.. module:: state
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from enum import Enum
import os
from pathlib import Path
import sys

script_path = Path(os.path.realpath(__file__)).parent
sys.path.append(script_path)
help_docs_dir = Path(script_path) / "help_docs"


class PageID(Enum):
    SIM_SELECT_PAGE = 1
    SIM_INFO_PAGE = 2
    MODEL_PARAMS_PAGE = 3
    DOSING_PKDATA_PAGE = 4
    SIM_RUN_PAGE = 5
    SIM_RESULTS_PAGE = 6
    PLOTS_PAGE = 7
    TABLES_PAGE = 8


class SimType(Enum):
    FORWARD = 1
    MONTE_CARLO = 2
    PARAMETER_EST = 3
    PARAMETER_EST_PLUS_MONTE_CARLO = 4
    SENSITIVITY = 5
    SETPOINTS = 6


page_order = {
    SimType.FORWARD: (PageID.SIM_SELECT_PAGE, PageID.MODEL_PARAMS_PAGE),
    SimType.MONTE_CARLO: (PageID.SIM_SELECT_PAGE, PageID.MODEL_PARAMS_PAGE),
    SimType.PARAMETER_EST: (PageID.SIM_SELECT_PAGE, PageID.MODEL_PARAMS_PAGE),
    SimType.PARAMETER_EST_PLUS_MONTE_CARLO: (
        PageID.SIM_SELECT_PAGE,
        PageID.MODEL_PARAMS_PAGE,
    ),
    SimType.SENSITIVITY: (PageID.SIM_SELECT_PAGE, PageID.MODEL_PARAMS_PAGE),
    SimType.SETPOINTS: (PageID.SIM_SELECT_PAGE, PageID.MODEL_PARAMS_PAGE),
}

HELP_FILES = {
    PageID.SIM_SELECT_PAGE.value: help_docs_dir / "simselect.html",
    PageID.SIM_INFO_PAGE.value: help_docs_dir / "siminfo.html",
    PageID.MODEL_PARAMS_PAGE.value: help_docs_dir / "modelparams.html",
    PageID.DOSING_PKDATA_PAGE.value: help_docs_dir / "dosingpkdata.html",
    PageID.SIM_RUN_PAGE.value: help_docs_dir / "simrun.html",
    PageID.SIM_RESULTS_PAGE.value: help_docs_dir / "simresults.html",
}
