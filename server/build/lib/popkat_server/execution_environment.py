"""
.. module:: environment
   :synopsis: Extract relevant information from the model execution environment

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import datetime
import hashlib
import json
import os
import platform
import re
import string
import time
from collections import OrderedDict

from pip._internal.operations.freeze import freeze


def _get_hash(fpath):
    """Compute the hash of a file given the filepath"""
    hash_type = "sha256"
    h = hashlib.sha256()
    with open(fpath, "rb", buffering=0) as f:
        for b in iter(lambda: f.read(128 * 1024), b""):
            h.update(b)
    return hash_type, h.hexdigest()


def _timestamp(fmt="%Y%m%dT%H%M%S%f"):
    """Return the current date/time (local timezone) as a timestamp."""
    tstamp = datetime.datetime.now().strftime(fmt)
    return tstamp


def _strings(filename, min_=4):
    """Extract printable strings from a file

    The main intent is to get a listing of symbols from a compiled file
    Code taken from https://stackoverflow.com/questions/17195924/python-equivalent-of-unix-strings-utility#17197027
    """
    with open(filename, errors="ignore") as fh:
        result = ""
        for c in fh.read():
            if c in string.printable:
                result += c
                continue
            if len(result) >= min_:
                yield result
            result = ""
        if len(result) >= min_:  # catch result at EOF
            yield result


def extract_from_model(model_file):
    """Extract certain strings from the model file"""
    libs = ("so", "dll", "dylib", "lib")  # library-file extensions
    mcsim = ("mod.*v\d+.*",)  # mcsim-specific
    patt_libs = [f".*\.{x}" for x in libs]
    patt_mcsim = [f"{x}" for x in mcsim]
    patt_all = "|".join(patt_libs + patt_mcsim)
    regex_all = re.compile(rf"({patt_all})")
    results = []
    for s in set(_strings(model_file)):
        res = regex_all.search(s.lower())
        if res:
            results.append(res[0])
    return sorted(results)


def _get_python_modules(relevant_only=False):
    """Get a list of installed python modules"""
    relevant = ["rpyc", "numpy", "scipy", "pandas", "plotnine", "appdirs"]
    all_modules = list(freeze(local_only=True))
    if relevant_only:
        rmodules = []
        for mod in all_modules:
            for r in relevant:
                if r in mod:
                    rmodules.append(mod)
    else:
        rmodules = all_modules
    return sorted(rmodules)


def get_env(model_file):
    """Get various properties of the computational environment"""
    env_dict = OrderedDict()
    env_dict["timestamp"] = _timestamp()
    env_dict["sim_model"] = {}
    env_dict["platform"] = {}
    env_dict["os"] = {}
    env_dict["python"] = {}

    # get details about the compiled mcsim model
    env_dict["sim_model"]["name"] = os.path.basename(model_file)
    env_dict["sim_model"]["last_modified"] = time.ctime(os.path.getmtime(model_file))
    env_dict["sim_model"]["hash"] = "|".join(_get_hash(model_file))
    env_dict["sim_model"]["libs"] = extract_from_model(model_file)

    # get various platform-related information
    plat_attrs = ["node", "processor", "machine"]
    for attr in plat_attrs:
        env_dict["platform"][attr] = getattr(platform, attr)()

    # get various system-related information
    os_attrs = ["platform", "release", "version"]
    for attr in os_attrs:
        env_dict["os"][attr] = getattr(platform, attr)()

    # get python info (version and package list)
    py_attrs = ["python_version", "python_build"]
    for attr in py_attrs:
        env_dict["python"][attr] = getattr(platform, attr)()
    env_dict["python"]["packages"] = _get_python_modules()
    return env_dict


def write_env(model_file, outfile):
    """Write environment information in json-format to a file"""
    env_dict = get_env(model_file)
    with open(outfile, "w") as fh:
        json.dump(env_dict, fh)
