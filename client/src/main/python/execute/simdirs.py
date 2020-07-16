"""
.. module:: simdirs
   :synopsis: Directory creation for PoPKAT simulations

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import os
from pathlib import PurePath

import appdirs

from utils import gen_utils, shared
from config.settings import LOCAL_BASE_DIR, MODELS_BASE_DIR, REMOTE_BASE_DIR
from config.consts import APP_AUTHOR, APP_NAME, APP_SERVER_NAME

SimInfo = shared.SimInfo()


def get_remote_models_dir(remote):
    """Retrieve the remote directory that stores models"""
    r_pathlib = remote.modules.pathlib
    r_appdirs = remote.modules.appdirs
    user_data_dir = r_appdirs.user_data_dir(APP_SERVER_NAME, APP_AUTHOR)
    mdir = r_pathlib.PurePath(user_data_dir) / MODELS_BASE_DIR
    return mdir


def create_remote_work_dir(remote):
    """Create the remote work dir"""
    tempdir = create_temp_dir_name()
    date = gen_utils.timestamp(fmt="%Y%m%d")
    r_pathlib = remote.modules.pathlib
    r_os = remote.modules.os
    r_appdirs = remote.modules.appdirs
    user_data_dir = r_appdirs.user_data_dir(APP_SERVER_NAME, APP_AUTHOR)
    rwork_dir = r_pathlib.PurePath(user_data_dir) / REMOTE_BASE_DIR / date / tempdir
    r_os.makedirs(rwork_dir, exist_ok=True)
    return rwork_dir


def create_local_work_dir():
    """Create the local working directory"""
    tempdir = create_temp_dir_name()
    date = gen_utils.timestamp(fmt="%Y%m%d")
    user_data_dir = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
    full_dir = PurePath(user_data_dir) / LOCAL_BASE_DIR / date / tempdir
    os.makedirs(full_dir, exist_ok=True)
    return full_dir


def create_local_work_subdirs(local_work_dir):
    """Create necessary subdirectories of the local working directory"""
    sdirs = dict(
        sim_infile_dir=local_work_dir / "input",
        sim_outfile_dir=local_work_dir / "results",
        sim_posteriors_dir=local_work_dir / "results" / "posteriors",
        sim_plots_dir=local_work_dir / "results" / "plots",
        sim_tables_dir=local_work_dir / "results" / "tables",
    )
    for sd in sdirs.values():
        os.makedirs(sd, exist_ok=True)
    return sdirs


def create_temp_dir_name(prefix="tmp", rbytes=8):
    """Create a temporary file name

    We might be able to use the tempfile module for this, but it allows us
    to repeat the name if needed
    """
    temp_dir_name = f"{prefix}_{gen_utils.create_id(rbytes=rbytes)}"
    return temp_dir_name


# ------------------------------------------------------------------------------


def create_local_dirs():
    local_work_dir = create_local_work_dir()
    subdirs = create_local_work_subdirs(local_work_dir)
    SimInfo.sim_dirs["local_work_dir"] = local_work_dir
    SimInfo.sim_dirs.update(subdirs)


def create_remote_dirs(remote):
    """Create all of the required local and remote directories"""
    remote_models_dir = get_remote_models_dir(remote)
    remote_work_dir = create_remote_work_dir(remote)
    SimInfo.sim_dirs["remote_models_dir"] = remote_models_dir
    SimInfo.sim_dirs["remote_work_dir"] = remote_work_dir
