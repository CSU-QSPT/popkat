"""
.. module:: utils
   :synopsis: Utilities used in popkat analyses

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import datetime
import errno
import hashlib
import json
import os
import re
import socket
import tempfile
from functools import reduce
from operator import getitem
from pathlib import Path

import pandas as pd
import rpyc
from plotnine import theme, theme_bw

from config.consts import CONCAT_FILE_SEP, POPULATION_KEYWORD, POSTERIOR_BASENAME
from config.settings import DEFAULT_HOST, DEFAULT_SERVER_PORT, LASTN_PTS

ITEM_SEPARATORS = re.compile("[,;\s]")


# ------------------------------------------------------------------------------
# exceptions
# ------------------------------------------------------------------------------
class PoPKATUtilsError(Exception):
    """Exception type for the PoPKAT utils"""


# ------------------------------------------------------------------------------
# general utils
# ------------------------------------------------------------------------------
def create_id(rbytes=16):
    """Create a random (or pseudo-random) identifier"""
    r_id = os.urandom(rbytes).hex()
    return r_id


def to_list(val):
    """Convert a value to a list.

    :param val: value to convert (or contain within) a list
    """
    if isinstance(val, Path):
        val = str(val)
    if isinstance(val, (str, int, float)):
        plist = [val]
    else:
        try:
            plist = list(val)
        except Exception:
            raise ValueError("Error: Input must be convertible to a list")
    return plist


def hash_file(fpath):
    """Compute the hash of a file given the filepath"""
    h = hashlib.sha256()
    with open(fpath, "rb", buffering=0) as f:
        for b in iter(lambda: f.read(128 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def find_files(fname, path):
    """Return a list of the paths to file fname in the specified directory path"""
    result = []
    for root, dirs, files in os.walk(path):
        if fname in files:
            result.append(os.path.join(root, fname))
    return result


def separate(fpath):
    """Separate a single file's contents into a series of files based on a separator"""
    results = []
    sdir = Path(tempfile.mkdtemp(prefix="pkt_"))
    with open(fpath, "r") as fi:
        contents = fi.read()  # this will be problematic for very large files
        chunks = contents.split(CONCAT_FILE_SEP)
        for i, chnk in enumerate(chunks):
            outfile = sdir / f"file_{i:03d}"
            with open(outfile, "w") as fo:
                fo.write(chnk)
                fo.write("\n")
            results.append(outfile)
    return results


def concatenate(fpaths):
    """Concatenate the contents of a list of files to a single file"""
    nfiles = len(fpaths)
    if len(fpaths) == 1:
        outfile = fpaths[0]
    else:
        _, outfile = tempfile.mkstemp()
        with open(outfile, "w") as fo:
            for i, fname in enumerate(fpaths):
                with open(fname, "r") as fi:
                    content = fi.read()
                    fo.write(content)
                    if i != nfiles - 1:
                        fo.write(CONCAT_FILE_SEP)
    return outfile


def timestamp_to_datetime(timestamp, fmt="%Y%m%dT%H%M%S%f"):
    """Convert an internal timestamp to a datetime object"""
    dtime = datetime.datetime.strptime(timestamp, fmt)
    return dtime


def timestamp(fmt="%Y%m%dT%H%M%S%f"):
    """Return the current date/time (local timezone) as a timestamp."""
    tstamp = datetime.datetime.now().strftime(fmt)
    return tstamp


def no_op(val):
    """Return the input argument unchanged"""
    return val


def text_to_list(txt, to_float=True):
    """Turn a text string consisting of separate entries to a python list"""
    items = ITEM_SEPARATORS.split(txt)
    if to_float:
        litems = [float(x) for x in items if x]
    else:
        litems = [x for x in items if x]
    return litems


def list_to_str(lst, sep=", "):
    """Convert a 'list' into a string, e.g., '1, 2, 3'
    """
    txt = sep.join([str(x) for x in lst])
    return txt


# ------------------------------------------------------------------------------
# utils for determining the monotonicity of a sequence
# from https://stackoverflow.com/a/4985520
# ------------------------------------------------------------------------------
def pairwise(seq):
    """Yield overlapping pairs in a sequence"""
    items = iter(seq)
    last = next(items)
    for item in items:
        yield last, item
        last = item


def strictly_increasing(L):
    """Is a sequence strictly increasing"""
    return all(x < y for x, y in pairwise(L))


def strictly_decreasing(L):
    """Is a sequence strictly increasing"""
    return all(x > y for x, y in pairwise(L))


def non_increasing(L):
    """Is a sequence non-increasing (decreasing or constant)"""
    return all(x >= y for x, y in pairwise(L))


def non_decreasing(L):
    """Is a sequence non-decreasing (increasing or constant)"""
    return all(x <= y for x, y in pairwise(L))


# ------------------------------------------------------------------------------
# network-related utils
# ------------------------------------------------------------------------------
def connect(host=DEFAULT_HOST, port=DEFAULT_SERVER_PORT):
    """Connect to a server, creating a tcp and socket connection

    :param host: host ip address
    :param port: port number
    """
    try:
        conn = rpyc.classic.connect(host, port=port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.connect((host, port))
    except ConnectionRefusedError:
        errmsg = (
            "ConnectionRefusedError: Make sure that the server is "
            + f"running on {host} and that port {port} is open."
        )
        raise PoPKATUtilsError(errmsg)
    return conn, sock


def is_localhost(ip_addr):
    """Determine if host is on the local machine

    The method below relies on the ability to bind an ip address.
    It may not be very robust.
    """
    s = socket.socket()
    try:
        try:
            s.bind((ip_addr, 0))
        except OSError as e:
            if e.args[0] == errno.EADDRNOTAVAIL:
                return False
            else:
                raise
    finally:
        s.close()
    return True


# ------------------------------------------------------------------------------
# analysis-related utils
# ------------------------------------------------------------------------------
def get_known_dists():
    """MCSim distributions as of MCSim 6.0.1."""
    # {dist name: number of arguments, ...}
    all_dists = {
        "Beta": 2,
        "Binomial": 2,
        "Cauchy": 1,
        "Chi2": 1,
        "Exponential": 1,
        "Gamma": 2,
        "HalfCauchy": 1,
        "HalfNormal": 1,
        "InvGamma": 2,
        "LogNormal": 2,
        "LogNormal_v": 2,
        "LogUniform": 2,
        "Normal": 2,
        "Normal_cv": 2,
        "Normal_v": 2,
        "Piecewise": 4,
        "Poisson": 1,
        "StudentT": 3,
        "TruncInvGamma": 4,
        "TruncLogNormal": 4,
        "TruncLogNormal_v": 4,
        "TruncNormal": 4,
        "TruncNormal_cv": 4,
        "TruncNormal_v": 4,
        "Uniform": 2,
    }
    # {dist name: arguments, ...}
    allowed_dists = {
        "Uniform": ("min", "max"),
        "LogUniform": ("min", "max"),
        "Normal": ("mean", "std"),
        "Normal_v": ("mean", "var"),
        "LogNormal": ("mean", "std"),
        "LogNormal_v": ("mean", "var"),
        "TruncNormal": ("mean", "std", "min", "max"),
        "TruncNormal_v": ("mean", "var", "min", "max"),
        "TruncLogNormal": ("mean", "std", "min", "max"),
        "TruncLogNormal_v": ("mean", "var", "min", "max"),
    }
    return allowed_dists


def parse_mcsim_messages(output):
    """Parse the simulation output (stdout) from MCSim.

    :param output: stdout messages"""
    fp_regex = re.compile(r"(?P<num>([+-])?\d+\.\d+)")
    sentinel = "PB:"
    if sentinel in output:
        vals = output.split()
        pvals = []
        for v in vals:
            result = fp_regex.search(v)
            if result:
                pvals.append(result["num"])
    else:
        pvals = []
    return pvals


def get_from_json(filename, info):
    """Get object values from a json file as return as a dict

    filename (path): path to json file to be queried
    info (dict): keys are desired return keys and values are
                 tuples, where each tuple is the location of the
                 information in the object (key, subkey, sub-subkey, ...)
    """
    results = {}
    with open(filename, "r") as fh:
        contents = json.load(fh)
    for n, l in info.items():
        val = reduce(getitem, l, contents)
        results[n] = val
    return results


def collect_file_paths(fdir, types):
    """Get a collection of file paths based on specified types"""
    results = {}
    for t in types:
        pattern = f"**/*.{t}"
        results[t] = list(Path(fdir).glob(pattern))
    return results


def path_to_filename(fpath):
    """Extract the filename from a file path"""
    if isinstance(fpath, Path):
        fname = fpath.name
    elif isinstance(fpath, str):
        fname = os.path.basename(fpath)
    else:
        errmsg = "Inappropriate path format: must be either str or pathlib.Path"
        raise TypeError(errmsg)
    return fname


def get_run_id(fname):
    """Extract run id from file name"""
    fname = Path(fname)
    _, run_id = fname.stem.split("_")
    return run_id


def extract_name_and_level(col_name, sim_type="mc", toplevel=1):
    """Split an MCMC column name into the root name and the hierarchical
    level."""
    mcmc_regex = re.compile(r"((?P<name>\w+)\((?P<level>\d+(\.\d+)?)\))")
    mc_regex = re.compile(fr"(?P<name>\w+)_(?P<level>{toplevel}\.\d+)")
    sim_type_regex = {"mcmc": mcmc_regex, "mc": mc_regex}
    result = sim_type_regex[sim_type].search(col_name)
    if result:
        name, level = result["name"], result["level"]
    else:
        name, level = None, None
    return name, level


def update_id(hvar):
    """Rename a hierarchical results variable to a more descriptive value.

    :param hvar: name of a hierarchical results variable (e.g., 1.2)
    """
    # get an identifier for the data subset
    # (1) -> 'pop'
    # (1.#) -> 's#'
    if "." not in hvar:
        id_ = POPULATION_KEYWORD
    else:
        sublevel = hvar.split(".")[1].zfill(2)
        id_ = f"s{sublevel}"
    return id_


def split_mcmc_posteriors(
    mcmc_outfile, save_dir, lastn_pts=LASTN_PTS, basename=POSTERIOR_BASENAME
):
    """Split a hierarchical MCMC file into separate files for each level.
    These files can then be used for MCSim setpoints analyses.

    :param mc_outfiles: iterable of MC output file paths
    :param save_dir: path to directory into which the individual posterior files
       should be saved
    :param lastn_pts: number of points to use from the end of the
       chains (0=all)
    """
    all_dat = split_mcmc_output(mcmc_outfile, lastn_pts=lastn_pts)
    save_posteriors(all_dat, save_dir, basename=basename)


def save_posteriors(all_dat, save_dir, basename=POSTERIOR_BASENAME):
    """Save posteriors that were split from a hierarchical MCMC output file.

    :param all_dat: mapping of name/id to dataframes that contain posterior
       distributions
    :param save_dir: path to directory into which the individual posterior
       files should be saved
    :param basename: basename for files
    """
    for name, df in all_dat.items():
        fname = Path(save_dir, f"{basename}_{name}.txt")
        df.to_csv(fname, sep="\t", encoding="utf-8", index=False)


def split_mcmc_output(mcmc_outfile, lastn_pts=LASTN_PTS):
    """Split an MCMC output file into subsets: one file for the
    population and one for each subject.
    The functionality of this function is tied depends directly
    to the hierarchy of the mcmc sim file.
    This function is extremely inefficient, approx O(N^2).

    :param mcmc_outfile: path to MCMC output file
    :param lastn_pts: number of points to use from the end of the chains (0=all)
    """
    df = pd.read_csv(mcmc_outfile, sep="\t")
    if lastn_pts:
        df = df[-lastn_pts:]
    cols = df.columns
    levels, all_dat = set(), {}
    # get the level run number that is contained in the parentheses
    for c in cols:
        name, level = extract_name_and_level(c, sim_type="mcmc")
        if level:
            levels.add(level)
    # create a datastructure with the posteriors for the population and for
    # each individual
    for l in levels:
        name = update_id(l)
        clevel = [c for c in cols if f"({l})" in c]
        sub_df = df[clevel].copy()
        # rename the columns, removing the level run numbers
        # also add an index column, which is necessary for a setpoints analysis
        sub_df.rename(
            columns=lambda x: extract_name_and_level(x, sim_type="mcmc")[0],
            inplace=True,
        )
        sub_df.insert(0, "iter", range(len(sub_df)))
        all_dat[name] = sub_df
    return all_dat


def sim_output_filter(line):
    """Filter output from the MCSim simulation"""
    line = line.strip()
    if line.startswith("Iteration"):
        _, inum = line.split()
        fline = "PB: {inum}"
    return fline


# ------------------------------------------------------------------------------
# plotnine package customized themes
# ------------------------------------------------------------------------------
class theme_bw_wide(theme_bw):
    """Customized plotnine theme"""

    def __init__(self, panel_spacing_x=0.5):
        theme_bw.__init__(self)
        self.add_theme(theme(panel_spacing_x=panel_spacing_x), inplace=True)
