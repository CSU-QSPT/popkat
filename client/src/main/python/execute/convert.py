"""
.. module:: convert
   :synopsis: Functionality to convert a simulation specifications file to MCSim files

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import copy
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from utils import gen_utils
from utils import shared
from config.settings import NUM_TIME_PTS
from config.consts import PROBLEM_MARKER, SIM_FILE_SUFFIXES

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = str(
    SCRIPT_DIR / "templates"
)  # this has to be a string to be compatible with jinja2

CLN_REGEX = re.compile("[ \";']")  # a regex used to clean parameters

SimInfo = shared.SimInfo()


class MCSimFileWriter(object):
    """Translate a data structure of simulation specifications to an MCSim
    input file"""

    def __init__(
        self,
        sim_specs,
        sim_infile_dir,
        sim_outfile_dir,
        setpts_data_file=None,
        sim_type=None,
        run_id="",
    ):
        """Retrieve the appropriate template file and apply it to the data."""
        sim_infile, sim_outfile = self._create_filespaces(
            sim_infile_dir, sim_outfile_dir, run_id=""
        )
        self.sim_infile = sim_infile
        self.sim_outfile = sim_outfile
        # Note: sim_type can be different from that specified in the popkat file;
        # however, inconsistencies can result
        if not sim_type:
            sim_type = SimInfo.sim_type
        if "setpt" in sim_type and not setpts_data_file:
            err_msg = (
                "Error: Converting to a setpt analysis file "
                "requires the specification of a setpoint data file"
            )
            raise gen_utils.PoPKATUtilsError(err_msg)
        self._render(
            sim_type, sim_specs, sim_outfile, setpts_data_file=setpts_data_file
        )

    def _render(self, sim_type, sim_specs, sim_outfile, setpts_data_file=None):
        """Render the input file based on the popkat file and template."""
        sim_map = {
            "mcmc": ("mcsim_mcmc_file_template.j2", self._to_mcmc),
            "mc": ("mcsim_mc_file_template.j2", self._to_mc),
            "fwd": ("mcsim_fwd_file_template.j2", self._to_fwd),
            "setpts": ("mcsim_setpts_file_template.j2", self._to_setpts),
            "sens": ("mcsim_sens_file_template.j2", self._to_sens),
        }
        template, processor = sim_map[sim_type]
        jinja_environment = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR), trim_blocks=False, lstrip_blocks=True
        )
        template = jinja_environment.get_template(template)
        sim_specs = self._classify_params(sim_specs)
        processed_vars = processor(sim_specs)
        # there is additional information that is not necessarily appropriate
        # for the popkat file but is useful in rendering the MCSim files;
        # inject that information here
        processed_vars["meta_info"]["out_file"] = sim_outfile
        processed_vars["meta_info"]["setpts_data_file"] = setpts_data_file
        processed_vars["render_timestamp"] = gen_utils.timestamp()
        # render the template
        self.output = template.render(processed_vars)

    def _create_filespaces(self, sim_infile_dir, sim_outfile_dir, run_id=""):
        """Create filenames based on the sim_id"""
        sim_id = SimInfo.sim_geninfo["sim_id"]
        Path(sim_infile_dir).mkdir(exist_ok=True)
        Path(sim_outfile_dir).mkdir(exist_ok=True)
        input_suf = SIM_FILE_SUFFIXES["input_file"]
        output_suf = SIM_FILE_SUFFIXES["output_file"]
        if run_id:
            run_id = "_" + run_id
        sim_infile = Path(sim_infile_dir) / f"{sim_id}{run_id}.{input_suf}"
        sim_outfile = Path(sim_outfile_dir) / f"{sim_id}{run_id}.{output_suf}"
        return sim_infile, sim_outfile

    def write(self):
        """Write the final rendered output file."""
        with open(self.sim_infile, "w") as fh:
            fh.write(self.output)

    # --------------------------------------------------------------------------
    # Methods for converting to each file type
    # These methods are very tightly coupled with their respective
    # templates; changes there may affect the code here and vice versa
    # --------------------------------------------------------------------------
    def _to_mcmc(self, sim_specs):
        """Alter information from the popkat file data so that it is compatible
        with Markov chain Monte Carlo (MCMC) analyses."""
        processed_vars = copy.deepcopy(sim_specs)
        params_key = "pkdata"
        pkdata = sim_specs[params_key]
        sampled_variables = set()
        # PK data
        for subject_id, data in pkdata.items():
            for trial_id, d in data.items():
                dtype, damounts, dtimes = (
                    d["dosing_type"],
                    d["dose_amounts"],
                    d["dosing_times"],
                )
                regimen = self._to_regimen(dtype, dtimes, damounts)
                sv = d["sampled_variable"]
                sampled_variables.add(sv)
                processed_vars[params_key][subject_id][trial_id][
                    "dosing_regimen"
                ] = regimen
        processed_vars.update({"sampled_variables": sampled_variables})
        return processed_vars

    def _to_fwd(self, sim_specs):
        """Alter information from the popkat file data so that it is compatible
        with scalar input (forward) analyses."""
        processed_vars = copy.deepcopy(sim_specs)
        # dosing info
        regimen = self._dosing_to_regimen(sim_specs)
        processed_vars.update({"dosing": regimen})
        processed_vars["sim_params"]["t_step"] = self._compute_time_step(sim_specs)
        return processed_vars

    def _to_mc(self, sim_specs):
        """Alter information from the popkat file data so that it is compatible
        with Monte Carlo (MC) analyses."""
        processed_vars = copy.deepcopy(sim_specs)
        # dosing info
        regimen = self._dosing_to_regimen(sim_specs)
        processed_vars.update({"dosing": regimen})
        processed_vars["sim_params"]["t_step"] = self._compute_time_step(sim_specs)
        return processed_vars

    def _to_setpts(self, sim_specs, setpts_data_file=None):
        """Alter information from the popkat file data so that it is compatible
        with SetPoints analyses."""
        processed_vars = copy.deepcopy(sim_specs)
        # dosing info
        regimen = self._dosing_to_regimen(sim_specs)
        processed_vars.update({"dosing": regimen})
        processed_vars["sim_params"]["t_step"] = self._compute_time_step(sim_specs)
        return processed_vars

    def _to_sens(self, sim_specs, setpts_data_file=None):
        """Alter information from the popkat file data so that it is compatible
        with a sensitivity and SetPoints analyses."""
        processed_vars = copy.deepcopy(sim_specs)
        # dosing info
        regimen = self._dosing_to_regimen(sim_specs)
        processed_vars.update({"dosing": regimen})
        processed_vars["sim_params"]["t_step"] = self._compute_time_step(sim_specs)
        # values for the sensitivity analysis
        sspecs = sim_specs["sens_params"]
        snames, sbounds, snum = [], [], len(sspecs)
        for svar in sspecs:
            snames.append(str(svar["name"]))
            low, high = svar["min"], svar["max"]
            sbounds.append([low, high])
        sinfo = (
            ["num_vars", snum],
            ["names", snames],
            ["bounds", sbounds],
            ["problem_delim", PROBLEM_MARKER],
        )
        processed_vars["sensitivity_info"] = {k: v for k, v in sinfo}
        return processed_vars

    # --------------------------------------------------------------------------
    # various helper functions
    # --------------------------------------------------------------------------
    def _classify_params(self, sim_specs):
        """Detect param type (scalar, distribution, or estimated) and store
        them in separate structures.
        """
        split_params = copy.deepcopy(sim_specs)
        model_params = sim_specs["model_params"]
        variability = sim_specs["model_param_variability"]
        sensitivity = sim_specs["model_param_sensitivity"]
        # loop through all of the model parameters, putting each into one
        # of three bins: estimated params, distributions, scalar params
        scalar_params, dist_params = {}, []
        est_params, sens_params = [], []
        for clsf, params in model_params.items():
            for p in params:
                name, value, for_estimation, for_sensitivity = (
                    p["name"],
                    p["value"],
                    p["for_estimation"],
                    p["for_sensitivity"],
                )
                if for_estimation:
                    ep = self._process_est_param(p, variability)
                    est_params.append(ep)
                if for_sensitivity:
                    sp = self._process_sens_param(p, sensitivity)
                    sens_params.append(sp)
                if (not for_estimation) and (not for_sensitivity):
                    if self._is_dist(value):
                        dmap = self._parse_dist(name, value)
                        dist_params.append(dmap)
                    else:
                        scalar_params.setdefault(clsf, []).append(p)
        # include the individual bins, but remove the aggregate one
        split_params["scalar_params"] = scalar_params
        split_params["dist_params"] = dist_params
        split_params["est_params"] = est_params
        split_params["sens_params"] = sens_params
        del split_params["model_params"]
        return split_params

    def _compute_time_step(self, sim_specs):
        """Calculat the time step based on user inputs and preferences"""
        sim_params = sim_specs["sim_params"]
        t_start = sim_params["t_start"]
        t_end = sim_params["t_end"]
        t_step = sim_params.get("t_step", None)
        if not t_step:
            t_step = float(t_end - t_start) / (NUM_TIME_PTS - 1)
        return t_step

    def _process_est_param(self, param, variability, rfactor=1000):
        """Determine and assemble the properties of an estimated variable.

        The properties are assembled assuming that both the population-level
        distribution and the individual-level distributions
        are LogNormal_v

        NOTE: The methodology used here is not rigorous.
        The distributions and arguments will need to be tested thoroughly.
        """
        name, value = param["name"], param["value"]
        cv_pop, cv_ind = variability["cv_pop"], variability["cv_ind"]
        # for a lognormal distribution, the cv does not depend on the mean
        ind_var = 1 + cv_ind ** 2
        pop_var = 1 + cv_pop ** 2
        est_param_spec = {
            "name": name,
            "mean": None,
            "args": None,
            "pop_var": pop_var,
            "ind_var": ind_var,
            "min": None,
            "max": None,
        }
        if self._is_dist(value):
            ep = self._parse_dist(name, value)
            est_param_spec.update(ep)
        else:
            mean = float(value)
            dmin = mean / rfactor
            dmax = mean * rfactor
            est_param_spec.update({"mean": mean, "min": dmin, "max": dmax})
        return est_param_spec

    def _process_sens_param(self, param, sensitivity):
        """Determine and assemble the properties of a parameter meant
        for sensitivity analysis.

        NOTE: The methodology used here is not rigorous.
        The distributions and arguments will need to be tested thoroughly.
        """
        name, value = param["name"], param["value"]
        low_factor = sensitivity["low_factor"]
        high_factor = sensitivity["high_factor"]
        sens_param_spec = {"name": name, "mean": None, "min": None, "max": None}
        if self._is_dist(value):
            sp = self._parse_dist(name, value)
            sens_param_spec.update(sp)
        else:
            mean = float(value)
            dmin = mean / low_factor
            dmax = mean * high_factor
            sens_param_spec.update({"mean": mean, "min": dmin, "max": dmax})
        return sens_param_spec

    def _to_regimen(self, dosing_type, dtimes, magnitudes):
        """Create the appropriate MCSim file lines for dosing."""
        # dose_type: (file_text, input function, duration)
        # NOTE: the value of duration is somewhat arbitrary
        dmap = {
            "oral": ("PO_dose", "NDoses", None),
            "oral-rate": ("Oral_dose_rate", "NDoses", 0.1),
            "iv": ("IV_dose_rate", "NDoses", 0.01),
        }
        try:
            varname, ftype, duration = dmap[dosing_type]
        except KeyError:
            errmsg = f"Error: Unknown dosing option: {dosing_type}"
            raise gen_utils.PoPKATUtilsError(errmsg)
        if duration is not None:
            ndoses, magnitudes, dtimes = self._assemble_input_args(
                dtimes, magnitudes, duration
            )
        else:
            ndoses = len(dtimes)
            dtimes = _list_to_string(dtimes)
            magnitudes = _list_to_string(magnitudes)
        regimen = f"{varname} = {ftype}({ndoses}, {magnitudes}, {dtimes})"
        return regimen

    def _assemble_input_args(self, dtimes, magnitudes, duration):
        """Construct the argument list for the relevant MCSim input function
        (e.g., NDoses).
        """
        # the number of time and magnitude values must be the same
        len_dtimes, len_magnitudes = len(dtimes), len(magnitudes)
        if len_dtimes != len_magnitudes:
            errmsg = (
                f"Error: The number of time and dose magnitudes must "
                + f"be the same: {len_dtimes} != {len_magnitudes}"
            )
            raise gen_utils.PoPKATUtilsError(errmsg)
        # sort values by increasing time
        dtimes, magnitudes = zip(*sorted(zip(dtimes, magnitudes)))
        # create input arguments
        start_times = dtimes.copy()
        stop_times = [dt + duration for dt in dtimes]
        start_rates = [m / duration for m in magnitudes]
        stop_rates = [0] * len(magnitudes)
        times = [i for s in zip(start_times, stop_times) for i in s]
        magnitudes = [i for s in zip(start_rates, stop_rates) for i in s]
        if start_times[0] != 0:
            times = [0] + times
            magnitudes = [0] + magnitudes
        # make sure the resulting time values are monotonically increasing
        # in value
        stimes = _list_to_string(times)
        if not gen_utils.strictly_increasing(times):
            errmsg = (
                f"Error: The dosing time sequence is not "
                + f"monotonically increasing: {stimes}"
            )
            raise gen_utils.PoPKATUtilsError(errmsg)
        ndoses = len(times)
        smagnitudes = _list_to_string(magnitudes)
        return ndoses, smagnitudes, stimes

    def _dosing_to_regimen(self, sim_specs):
        """Convert a dosing statement into a MCSim-writable regimen."""
        d = sim_specs["dosing"]
        dtype, damounts, dtimes = d["dosing_type"], d["dose_amounts"], d["dosing_times"]
        regimen = self._to_regimen(dtype, dtimes, damounts)
        return regimen

    def _is_dist(self, val):
        """Check value against known distributions."""
        known_dists = gen_utils.get_known_dists()
        val = re.sub(CLN_REGEX, "", val)  # remove extraneous chars from value
        idist = val.startswith(tuple(known_dists.keys()))
        return idist

    def _parse_dist(self, name, val):
        """Parse a parameter and break out the distribution terms if they
        exist and retrieve the type and arguments.
        This parser is not very robust. Input is assumed to be well formed.
        """
        known_dists = gen_utils.get_known_dists()
        dist_name = val[0 : val.find("(")].strip()
        dist_args = known_dists[dist_name]
        # get the values between the parentheses
        args = val[val.find("(") + 1 : val.find(")")].split(",")
        assert len(args) == len(known_dists[dist_name])
        # map the arguments to the distribution values
        dspec = dict(zip(dist_args, args))
        full_spec = {
            "name": name,
            "dist": dist_name,
            "args": args,
            "mean": None,
            "var": None,
            "min": None,
            "max": None,
        }
        full_spec.update(dspec)
        return full_spec


# ---------------------------------------------------------------------
# General utility functions
# ---------------------------------------------------------------------
def _list_to_string(l, sep=", "):
    """Convert a list to a string.

    :param sep: separator between list elements"""
    s = sep.join(map(str, l))
    return s


# ---------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------
def to_mcsim_input(
    sim_specs,
    sim_infile_dir,
    sim_outfile_dir,
    setpts_data_file=None,
    sim_type=None,
    run_id="",
):
    """Convert a PoPKAT simulation specification to an MCSim input file.

    :param sim_specs: data structure containing sim specifications
    :param sim_infile: path to save the generated input file
    :param sim_outfile: path to the output file that was written by the
       simulation engine
    :param setpts_data_file: path to the setpoints file (only required for
       'setpt' analysis)
    """
    mcsfw = MCSimFileWriter(
        sim_specs,
        sim_infile_dir,
        sim_outfile_dir,
        setpts_data_file=setpts_data_file,
        sim_type=sim_type,
        run_id=run_id,
    )
    mcsfw.write()
    return mcsfw.sim_infile, mcsfw.sim_outfile
