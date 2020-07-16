"""
.. module:: forward
   :synopsis: Functionality to analyze the 'forward' output from MCSim/PoPKAT
   simulations

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from pathlib import Path

import numpy as np
import pandas as pd
from plotnine import aes, facet_wrap, geom_line, geom_point, ggplot, labs, theme_bw

from config.settings import LINE_COLOR, MARKER_COLOR, PLOT_THEME

from .pkcalcs import calc_all_pk
from .popkatdata import PoPKATData


# ---------------------------------------------------------------------
# Forward analysis
# ---------------------------------------------------------------------


class FwdAnalyzer(object):
    """Produce plots and statistics related to 'forward' (scalar input)
    analyses"""

    def __init__(self, SimInfo, fwd_outfile):
        """Prepare a data structure by reading in a fwd output
        file. Also read in the params file to extract the experimental data.

        :param fwd_outfile: path to forward output file
           If applicable, the order should correspond to the order of data
        :param sim_specs: file path to popkat file
        """
        sim_specs = SimInfo.sim_specs
        self.fwd_outfile = fwd_outfile
        self.sim_id = SimInfo.sim_id
        if sim_specs:
            pkd = PoPKATData(sim_specs)
            self.pkdata = pkd.pkdata
        self._sim_info, self._data_info = self._process_files()
        self._pk_params = None
        self._all_plots = {}
        self._all_tables = {}

    def _process_files(self):
        """Read and parse files and return a data structure useful for plotting
        and analysis.
        """
        fwd_outfile = self.fwd_outfile
        pkdata = self.pkdata
        # process the simulation results prior to the data because
        # we need to extract the output variables first
        sim_res = self._process_sim()
        # process data
        if pkdata:
            data_res = self._process_data()
        return sim_res, data_res

    def _process_sim(self):
        """Create a mapping of output variable and dataframe of simulation
        results.

        :param sim_times: tuple of (start time, end time, time step)
        """
        NUM_HEADER_LINES = 2
        indep_var, indep_var_alias = "Time", "time"
        fwd_outfile = self.fwd_outfile
        pk_params = pd.DataFrame()
        # read and process each file
        sim_df = pd.read_csv(fwd_outfile, sep="\t", skiprows=NUM_HEADER_LINES)
        outvars = [x for x in sim_df.columns if x != indep_var]
        tidy_df = pd.melt(
            sim_df, id_vars=indep_var, var_name="measure", value_name="dep_var"
        )
        tidy_df.rename(columns={indep_var: indep_var_alias}, inplace=True)
        # set some object variables for access by other methods
        self._sim_df = sim_df
        self._pk_params = pk_params
        self._outvars = sorted(list(outvars))
        self._indep_var = indep_var
        return tidy_df

    def _process_data(self):
        """Create a mapping of output variable and dataframe of pk data,

        :param add_pop: boolean specifying whether to duplicate all data under
           a 'pop' id
        """
        pkdata = self.pkdata
        data_info = pd.DataFrame()
        for _, data in pkdata.items():
            # rename ids to simulation format
            for expt in data:
                pk_df = pd.DataFrame()
                pk_df["time"] = expt["sampling_times"]
                pk_df["dep_var"] = expt["sampled_values"]
                pk_df["measure"] = expt["sampled_variable"]
                data_info = data_info.append(pk_df)
        return data_info

    def _calc_pk_params(self, indep_var, dep_vars, df):
        """Calculate pharmacokinetic parameters.

        :param indep_var: name of independent variable, e.g. 'Time'
        :param dep_vars: iterable of dependent variable names
        :param df: dataframe containing simulation results
        """
        pk_all = []
        t = df[indep_var]
        for dep in dep_vars:
            C = df[dep]
            pk = calc_all_pk(t, C)  # dictionary
            pk_all.append(pk)
        pk_df = pd.DataFrame.from_dict(pk_all)
        pk_df.index = dep_vars
        return pk_df

    def plot(self, save_dir, width=11, height=8.5):
        """Wrapper for the various plot functions

        :param save_dir: directory into which plots should be saved
        :param width: width of plot in inches
        :param height: height of plot in inches
        """
        self._plot_pk_curves(save_dir, width=width, height=height)
        # self._plot_pk_residuals(save_dir, width=width, height=height)

    def _plot_pk_curves(self, save_dir, width=11, height=8.5):
        """Plot the pharmacokinetic curves with prediction intervals

        :param save_dir: directory into which plots should be saved
        :param width: width of plot in inches
        :param height: height of plot in inches
        """
        sim_df, data_df = self._sim_info, self._data_info
        if data_df.empty:
            # if we have no data, use a minimal dataframe so that the
            # commands below will still work
            data_df = pd.DataFrame(columns=["time", "dep_var"])
        # the ribbon should be drawn before the lines so that the lines
        # will be drawn on top
        p = (
            ggplot()
            + geom_line(
                sim_df,
                aes(x="time", y="dep_var"),
                color=LINE_COLOR,
                linetype="solid",
                size=1,
            )
            + geom_point(
                data_df, aes(x="time", y="dep_var"), color=MARKER_COLOR, alpha=0.7
            )
            + facet_wrap("~ measure")
            + theme_bw()
            + labs(y="Concentration", x="Time", title=f"Simulation results")
        )
        self._all_plots[f"fwd_pk"] = p.draw()
        fname = f"{self.sim_id}_fwd_pk.svg"
        fpath = Path(save_dir, fname)
        p.save(fpath, verbose=False, width=width, height=height)

    def _plot_pk_residuals(self, save_dir, width=11, height=8.5):
        """Create a plot of the difference between the data and predictions

        :param save_dir: directory into which plots should be saved
        :param width: width of plot in inches
        :param height: height of plot in inches
        """
        SimInfo, data_info = self._sim_info, self._data_info
        for ov in self._outvars:
            sim_df = SimInfo[ov]
            data_df = data_info[ov]
            if not (sim_df.empty or data_df.empty):
                diff_df = self._calc_df_diff(sim_df, data_df, ov)
                p = (
                    ggplot()
                    + geom_point(
                        diff_df,
                        aes(x="time", y="dep_var_diff"),
                        color=MARKER_COLOR,
                        alpha=0.7,
                        size=3,
                    )
                    + facet_wrap("~ ident")
                    + PLOT_THEME()
                    + labs(
                        y="Relative difference", x="Time", title=f"Variation in {ov}"
                    )
                )
                self._all_plots[f"mc_resid_{ov}"] = p.draw()
                fname = f"{self.sim_id}_mc_resid_{ov}.svg"
                fpath = Path(save_dir, fname)
                p.save(fpath, verbose=False, width=width, height=height)

    @staticmethod
    def _calc_df_diff(sim_df, data_df, ov):
        """Compute the relative difference between the simulation and data
        values

        :param sim_df: dataframe containing simulation results
        :param data_df: dataframe containing data values
        :param ov: output variable (e.g., C_central)
        """
        df_all = pd.DataFrame()
        idents = sim_df.ident.unique()
        for ident in idents:
            df = pd.DataFrame()
            t_dat, t_sim = data_df["time"], sim_df["time"]
            vals_dat, vals_sim = data_df["dep_var"], sim_df["dep_var"]
            vals_interp = np.interp(t_dat, t_sim, vals_sim)
            dep_var_diff = (vals_dat - vals_interp) / vals_dat
            df_vals = (("time", t_dat), ("dep_var_diff", dep_var_diff), ("measure", ov))
            for k, v in df_vals:
                df[k] = v
            df_all = df_all.append(df)
        return df_all

    def calc_pk_params(self, save_dir):
        """Compute various pk parameters for each of the dependent variables.

        :param save_dir: directory into which param tables should be saved
        """
        pk_df = self._calc_pk_params(self._indep_var, self._outvars, self._sim_df)
        self._all_tables["pk_params"] = pk_df.to_csv(path_or_buf=None, index=False)
        fname = f"{self.sim_id}_pk_params.txt"
        fpath = Path(save_dir, fname)
        with open(fpath, "w") as fh:
            fh.write(pk_df.to_csv(sep="\t", encoding="utf-8", float_format="%.4g"))


# ------------------------------------------------------------------------------


def analyze(
    fwd_outfile, sim_specs, plots_save_dir, stats_save_dir, width=11, height=8.5
):
    """Analyze forward analysis output file and generate plots.

    :param fwd_outfile: fwd simuation output file path
    :param sim_specs: path to the PoPKAT save file
    :param plots_save_dir: path to directory into which plot files should be
       saved
    """
    fwda = FwdAnalyzer(fwd_outfile, sim_specs)
    fwda.plot(plots_save_dir, width=width, height=height)
    fwda.calc_pk_params(stats_save_dir)
    results = {"plots": fwda._all_plots, "tables": fwda._all_tables}
    return results
