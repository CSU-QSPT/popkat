"""
.. module:: consts
   :synopsis: Various shared constants associated with MCSim/PoPKAT simulations

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from enum import Enum
import zipfile

# Enum used to select where popkat and mcsim messages should go


class MsgDest(Enum):
    STDOUT = 1
    SOCKET = 2
    NULL = 3


# Values used for directory creation
# These values *MUST* be the same as those in 'server_config.py'
APP_NAME = "popkat"
APP_SERVER_NAME = "popkat_server"
APP_AUTHOR = "qspt"

# Constants related to population analyses
POSTERIOR_BASENAME = "posterior"
POPULATION_KEYWORD = "pop"

# sim_type: (full_name, sim_details, uses_pkdata)
SIM_TYPES_INFO = {
    "fwd": {
        "full_name": "Forward",
        "analysis_details": [
            ("t_start", "Start time"),
            ("t_end", "End time"),
            ("t_step", "Number of time steps"),
        ],
        "uses_pkdata": False,
    },
    "mc": {
        "full_name": "Monte Carlo (MC)",
        "analysis_details": [
            ("t_start", "Start time"),
            ("t_end", "End time"),
            ("t_step", "Number of time steps"),
            ("rng_seed", "Random seed"),
            ("num_draws", "Number of draws"),
        ],
        "uses_pkdata": False,
    },
    "mcmc": {
        "full_name": "Parameter estimation (MCMC)",
        "analysis_details": [
            ("rng_seed", "Random seed"),
            ("num_iters", "Number of iterations"),
        ],
        "uses_pkdata": True,
    },
    "setpts": {
        "full_name": "Setpoints",
        "analysis_details": [("num_iters", "Number of iterations")],
        "uses_pkdata": False,
    },
    "sens": {
        "full_name": "Sensitivity",
        "analysis_details": [("num_iters", "Number of iterations")],
        "uses_pkdata": False,
    },
    "mcmc+setpts": {
        "full_name": "Parameter estimation + Setpoints",
        "analysis_details": [
            ("rng_seed", "Random seed"),
            ("num_iters", "Number of iterations"),
        ],
        "uses_pkdata": True,
    },
}

VALID_SIM_TYPES = list(SIM_TYPES_INFO.keys())

# code, name
VALID_DOSING_TYPES = {
    1: "Oral: slow release",
    2: "Oral: immediate release",
    3: "Intravenous",
}

# Create a mapping to most of the sensitivity analysis methods in SALib
# (see https://salib.readthedocs.io/en/latest/api.html)
#               method_alias: (sampler, analyzer)
SA_LIB_METHODS = {
    "fast": ("fast_sampler", "fast"),
    "rdb-fast": ("latin", "rdb_fast"),
    "morris": ("morris", "morris"),
    "sobol": ("saltelli", "sobol"),
    "delta": ("latin", "delta"),
    "ff": ("ff", "ff"),
}

# a special comment to note an SALib 'problem' section in the
# setpoints file used in the sensitivity analysis
PROBLEM_MARKER = "#-SA-#"

SIM_FILE_SUFFIXES = {
    "params_file": "prm",
    "env_file": "env",
    "output_file": "out",
    "input_file": "in",
    "model_exe": "exe",
    "table_file": "tab",
    "plot_file": "svg",
}

CONCAT_FILE_SEP = "<<<<<==========>>>>>"

DEFAULT_SAVE_FILE_NAME = "simulations"
DEFAULT_SAVE_FILE_SUFFIX = "pkt"

VALID_COMPRESSION_TYPES = {
    "bz2": zipfile.ZIP_BZIP2,
    "zip": zipfile.ZIP_DEFLATED,
    "lzma": zipfile.ZIP_LZMA,
}

# pharmacokinetic data table header information
# internal variable name: label, order in header
PKDATA_FIELDS = {
    "subject_id": ("Subject ID", 0),
    "trial_id": ("Trial ID", 1),
    "body_mass": ("Body mass", 2),
    "dosing_type": ("Dosing type flag", 3),
    "dosing_times": ("Dose administration times", 4),
    "dose_amounts": ("Administered dose amounts", 5),
    "sampling_times": ("Measurement time points", 6),
    "sampled_values": ("Measured concentrations", 7),
}

NULL_PKDATA_STRUCT = {
    "subject_01": {
        "trial_01": {
            "body_mass": "",
            "dose_amounts": [],
            "dosing_times": [],
            "dosing_type": "",
            "sampled_variable": "",
            "sampling_times": [],
            "sampled_values": [],
        }
    }
}
