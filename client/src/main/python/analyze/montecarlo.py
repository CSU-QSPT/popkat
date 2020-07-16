"""
.. module:: montecarlo
   :synopsis: Functionality to analyze the Monte Carlo output from MCSim/PoPKAT
              simulations

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import re
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from plotnine import (
    aes,
    facet_wrap,
    geom_hline,
    geom_line,
    geom_point,
    geom_ribbon,
    ggplot,
    labs,
    stat_boxplot,
    theme_bw,
)

from utils import shared, gen_utils
from config.settings import DASHED_LINE_COLOR, LINE_COLOR, MARKER_COLOR, PLOT_THEME
from utils.gen_utils import POPULATION_KEYWORD

from .pkcalcs import calc_pk_from_df
from .popkatdata import PoPKATData


# ------------------------------------------------------------------------------
# MC or Setpoints analysis
# ------------------------------------------------------------------------------


class MCAnalyzer(object):
    """Produce plots and statistics related to Monte Carlo analyses

    Note: We need to make sure that the simulation results and pk data
    correspond. The pk data should be in sorted order in the MCSim input file
    and therefore correspond to the hierarchical levels.
    We'll classify the levels as 'pop' (1), 's01' (1.1), 's02' (1.2), ...,
    's##' (1.##)
    """

    def __init__(self, SimInfo, mc_outfiles, label_with_sim_rnums=True):
        """Prepare a data structure by reading in one or more MC output
        files. Also read in the params file to extract the experimental data.

        Use simulation run numbers throughout. If the user chooses
        `label_with_sim_rnums=False`
        convert them in the plots and output.

        :param mc_outfiles: iterable of MC output file paths.
           If applicable, the order should correspond to the order of data
        :param sim_specs: file path to popkat file
        :param label_with_sim_rnums: True: display output results (plots, etc.)
           with sim run numbers for labels, False: use data ids for labels
        """
        self.label_with_sim_rnums = label_with_sim_rnums
        self._outvars = None
        self._pk_params_raw = None
        self.mc_outfiles = gen_utils.to_list(mc_outfiles)
        self._num_outfiles = len(self.mc_outfiles)
        self.sim_id = SimInfo.sim_id
        sim_specs = SimInfo.sim_specs
        self._all_plots = {}
        self._all_tables = {}
        if sim_specs:
            pkd = PoPKATData(sim_specs)
            self.pkdata = pkd.pkdata
            self._id_map = pkd.id_map
            self.sim_params = pkd.sim_params
            self._sim_rnum_to_data_id = pkd.sim_rnum_to_data_id
            self._data_id_to_sim_rnum = pkd.data_id_to_sim_rnum
            if label_with_sim_rnums:
                self._rename_id = gen_utils.no_op
            else:
                self._rename_id = pkd.sim_rnum_to_data_id
        self._pk_params = pd.DataFrame()
        self._sim_df, self._data_df = self._process_files(
            toplevel=1, pk_var="C_central", quants=(0.025, 0.5, 0.975), add_pop=True
        )

    def _process_files(
        self, toplevel=1, pk_var="C_central", quants=(0.025, 0.5, 0.975), add_pop=True
    ):
        """Read and parse files and return data structures useful for plotting
        and analysis.

        :param toplevel: the main hierarchical level
        :param pk_var: the output variable for which pk params should be
           computed
        :param quants: iterable of quantile values for confidence interval
           calculations
        :param add_pop: boolean specifying whether to duplicate all data under
           a 'pop' id
        """
        mc_outfiles = self.mc_outfiles
        pkdata, sim_params = self.pkdata, self.sim_params
        sim_times = [sim_params[t_] for t_ in ("t_start", "t_end", "t_step")]
        # process the simulation results prior to the data because
        # we need to extract the output variables first
        sim_df = self._process_sim(
            sim_times, toplevel=toplevel, pk_var=pk_var, quants=quants
        )
        # process data
        if pkdata:
            data_df = self._process_data(add_pop=add_pop)
        return sim_df, data_df

    def _extract_id(self, fpath):
        """If present, extract an id of the form 's##' from a filename;
        otherwise, return the next sim id from the list.

        For example:
          'posterior_s03.out' -> 's03'
          'posterior_test.out' -> 's##'
        """
        ids = list(self._id_map.keys())
        fname_regex = re.compile(r"\w+_(?P<ident>(s\d{2}|pop)).*")
        fname = Path(fpath).name
        result = fname_regex.search(fname)
        if result:
            id_ = result["ident"]
        else:
            id_ = ids.pop()
        return id_

    def _process_sim(
        self, sim_times, toplevel=1, pk_var="C_central", quants=(0.025, 0.5, 0.975)
    ):
        """Create a mapping of output variable and dataframe of simulation
        results.

        :param sim_times: tuple of (start time, end time, time step)
        :param toplevel: the main hierarchical level
        :param pk_var: the output variable for which pk params should be
           computed
        :param quants: iterable of quantile values for confidence interval
           calculations
        """
        mc_outfiles = self.mc_outfiles
        all_sim_df, sim_df = pd.DataFrame(), pd.DataFrame()
        pk_params = pd.DataFrame()
        all_outvars = set()
        for mcf in gen_utils.to_list(mc_outfiles):
            # try to extract the id from the filename itself
            # if not found, generate an id
            id_ = self._extract_id(mcf)
            # read and process each file
            outvars = set()
            df = pd.read_csv(mcf, sep="\t")
            col_names = df.columns.values.tolist()
            for c in col_names:
                name, _ = gen_utils.extract_name_and_level(
                    c, sim_type="mc", toplevel=toplevel
                )
                if name:
                    outvars.add(name)
                    all_outvars.add(name)
            for ov in outvars:
                # filter by columns that look like dependent variables
                # [e.g., concentrations (C_central_1.12)]
                rg = fr"{ov}_{toplevel}\.\d+"
                ndf = df.filter(regex=rg, axis=1)
                # compute some statistics
                lower, dep_var, upper = self._calc_confint(ndf, quants=quants)
                t_start, t_end, _ = sim_times
                # compute various PK measures
                tspan = np.linspace(t_start, t_end, len(lower))
                # compute statistics for the data associated with the pk_var
                # (probably C_central)
                if ov == pk_var:
                    stats_df = self._calc_pk_params_tidy(tspan, ndf, id_)
                    pk_params = pk_params.append(stats_df)
                # create a dataframe with the summary info
                # the order of these column assignments is important
                sim_df["time"] = tspan
                sim_df["lower"] = lower.values
                sim_df["dep_var"] = dep_var.values
                sim_df["upper"] = upper.values
                sim_df["ident"] = id_
                sim_df["measure"] = ov
                all_sim_df = all_sim_df.append(sim_df)
        # set some object variables for access by other methods
        self._pk_params = pk_params
        self._outvars = sorted(list(all_outvars))
        return all_sim_df

    def _process_data(self, add_pop=True):
        """Create a mapping of output variable and dataframe of pk data,

        :param add_pop: boolean specifying whether to duplicate all data under
           a 'pop' id
        """
        pkdata = self.pkdata
        outvars = self._outvars
        data_df = pd.DataFrame()
        for ident, data in pkdata.items():
            # rename ids to simulation format
            id_ = self._data_id_to_sim_rnum(ident)
            for expt in data:
                pk_df = pd.DataFrame()
                pk_df["time"] = expt["sampling_times"]
                pk_df["dep_var"] = expt["sampled_values"]
                pk_df["measure"] = expt["sampled_variable"]
                pk_df["ident"] = id_
                data_df = data_df.append(pk_df)
                if add_pop:
                    pk_df_pop = pk_df.copy()
                    pk_df_pop["ident"] = POPULATION_KEYWORD
                    data_df = data_df.append(pk_df_pop)
        return data_df

    def _calc_pk_params_tidy(self, tspan, df, id_):
        """Calculate pharmacokinetic parameters based on a dataframe and return
        the results in a 'tidy dataframe.

        :param tspan: iterable of time values
        :param df: dataframe, where each row contains concentration values as a
           function of time
        :param id_: identifier for the dataset (e.g., a subject number)
        """
        df_ = self._calc_pk_params(tspan, df)
        pk_labels = df_.columns.values.tolist()
        # for one mc_outfile, we leave the id_ blank
        df_["ident"] = id_
        df = pd.melt(
            df_,
            id_vars=["ident"],
            value_vars=pk_labels,
            var_name="param",
            value_name="value",
        )
        return df

    def _calc_pk_params(self, tspan, df):
        """Calculate pharmacokinetic parameters based on a dataframe.

        :param tspan: iterable of time values
        :param df: dataframe, where each row contains concentration values as a
           function of time
        """
        df = calc_pk_from_df(df, tspan)
        self._pk_params_raw = df
        return df

    def calc_pk_params(self, save_dir):
        """ident, param, value"""
        pk_params = self._pk_params
        ids = sorted(pk_params.ident.unique())
        params = sorted(list(pk_params.param.unique()))
        pk_dict = defaultdict(list)
        pk_dict["ident"] = []
        for id_ in ids:
            pk_dict["ident"].append(id_)
            for param in params:
                df = pk_params[
                    (pk_params["ident"] == id_) & (pk_params["param"] == param)
                ]
                mean_, std_ = df["value"].mean(), df["value"].std()
                val = f"{mean_:.4g} ({std_:.3g})"
                pk_dict[param].append(val)
        pk_df = pd.DataFrame.from_dict(pk_dict)
        self._all_tables["mc_pk_params"] = pk_df.to_csv(path_or_buf=None, index=False)
        fname = f"{self.sim_id}_mc_pk_params.txt"
        fpath = Path(save_dir, fname)
        with open(fpath, "w") as fh:
            fh.write(pk_df.to_csv(sep="\t", encoding="utf-8"))
        return pk_df

    def plot(self, save_dir, width=11, height=8.5):
        """Wrapper for the various plot functions

        :param save_dir: directory into which plots should be saved
        :param width: width of plot in inches
        :param height: height of plot in inches
        """
        if self._num_outfiles == 1:
            self._plot_pk_curves_sngl_sim(save_dir, width=width, height=height)
        self._plot_pk_curves_mult_sim(save_dir, width=width, height=height)
        self._plot_pk_params(save_dir, width=width, height=height)
        self._plot_pk_residuals(save_dir, width=width, height=height)

    def _pk_plot_base(self, sdf, ddf, facet_var, title):
        """Create a line plot with confidence intervals and data overlay"""
        # the ribbon should be drawn before the lines so that the lines
        # will be drawn on top
        p = (
            ggplot()
            + geom_ribbon(
                sdf,
                aes(x="time", ymin="lower", ymax="upper"),
                color="#fffafa",
                alpha=0.2,
            )
            + geom_line(
                sdf,
                aes(x="time", y="lower"),
                color=DASHED_LINE_COLOR,
                linetype="dashed",
                size=0.5,
            )
            + geom_line(
                sdf,
                aes(x="time", y="dep_var"),
                color=LINE_COLOR,
                linetype="solid",
                size=1,
            )
            + geom_line(
                sdf,
                aes(x="time", y="upper"),
                color=DASHED_LINE_COLOR,
                linetype="dashed",
                size=0.5,
            )
            + geom_point(ddf, aes(x="time", y="dep_var"), color=MARKER_COLOR, alpha=0.7)
            + facet_wrap(facet_var, labeller=self._rename_id)
            + PLOT_THEME()
            + labs(y="Concentration", x="Time", title=title)
        )
        return p

    def _plot_pk_curves_sngl_sim(self, save_dir, width=11, height=8.5):
        """Plot pharmacokinetic curves with prediction intervals for a single
        simulation, faceting by output variable

        :param save_dir: directory into which plots should be saved
        :param width: width of plot in inches
        :param height: height of plot in inches
        """
        sdf, ddf = self._sim_df, self._data_df
        if ddf.empty:
            # if we have no data, use a minimal dataframe so that the
            # commands below will still work
            ddf = pd.DataFrame(columns=["time", "dep_var"])
        facet_var = "~ measure"
        title = "Variation in pharmacokinetics across measures"
        p = self._pk_plot_base(sdf, ddf, facet_var, title)
        fname = f"{self.sim_id}_mc_pk.svg"
        self._all_plots["mc_pk"] = p.draw()
        fpath = Path(save_dir, fname)
        p.save(fpath, verbose=False, width=width, height=height)

    def _plot_pk_curves_mult_sim(self, save_dir, width=11, height=8.5):
        """Plot the pharmacokinetic curves with prediction intervals for
        multiple simulations, faceting them by data/sim id

        :param save_dir: directory into which plots should be saved
        :param width: width of plot in inches
        :param height: height of plot in inches
        """
        sim_df, data_df = self._sim_df, self._data_df
        facet_var = "~ ident"
        for ov in self._outvars:
            sdf = sim_df[sim_df["measure"] == ov]
            if not data_df.empty:
                ddf = data_df[data_df["measure"] == ov]
            else:
                # if we have no data, use a minimal dataframe so that the
                # commands below will still work
                ddf = pd.DataFrame(columns=["time", "dep_var"])
            title = f"Pharmacokinetics: mean and prediction intervals"
            p = self._pk_plot_base(sdf, ddf, facet_var, title)
            self._all_plots[f"mc_pk_{ov}"] = p.draw()
            fname = f"{self.sim_id}_mc_pk_{ov}.svg"
            fpath = Path(save_dir, fname)
            p.save(fpath, verbose=False, width=width, height=height)

    def _plot_pk_residuals(self, save_dir, width=11, height=8.5):
        """Create a plot of the difference between the data and predictions

        :param save_dir: directory into which plots should be saved
        :param width: width of plot in inches
        :param height: height of plot in inches
        """
        sim_df, data_df = self._sim_df, self._data_df
        facet_var = "~ ident" if (self._num_outfiles > 1) else "~ measure"
        for ov in self._outvars:
            sdf = sim_df[sim_df["measure"] == ov]
            ddf = data_df[data_df["measure"] == ov]
            if not (sdf.empty or ddf.empty):
                diff_df = self._calc_df_diff(sdf, ddf, ov)
                p = (
                    ggplot()
                    + geom_point(
                        diff_df,
                        aes(x="time", y="dep_var_diff"),
                        color=MARKER_COLOR,
                        alpha=0.7,
                        size=3,
                    )
                    + facet_wrap(facet_var, labeller=self._rename_id)
                    + PLOT_THEME()
                    + labs(
                        y="Relative difference",
                        x="Time",
                        title=f"Difference between predicted and data values for {ov}",
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
            ddf = data_df[data_df["ident"] == ident]
            sdf = sim_df[sim_df["ident"] == ident]
            t_dat, t_sim = ddf["time"], sdf["time"]
            vals_sim, vals_dat = sdf["dep_var"], ddf["dep_var"]
            vals_interp = np.interp(t_dat, t_sim, vals_sim)
            dep_var_diff = (vals_dat - vals_interp) / vals_dat
            df_vals = (
                ("time", t_dat),
                ("dep_var_diff", dep_var_diff),
                ("ident", ident),
                ("measure", ov),
            )
            for k, v in df_vals:
                df[k] = v
            df_all = df_all.append(df)
        return df_all

    def _plot_pk_params(self, save_dir, width=11, height=8.5):
        """Create a boxplot to show the variation in params.

        :param save_dir: directory into which plots should be saved
        :param width: width of plot in inches
        :param height: height of plot in inches
        """
        pk_params = self._pk_params
        p = (
            ggplot()
            + stat_boxplot(data=pk_params, mapping=aes(x="ident", y="value"))
            + facet_wrap("~ param", scales="free_y")
            + gen_utils.theme_bw_wide()
            + labs(
                y="Parameter",
                x="Subject",
                title="PK parameters derived from simulation results",
            )
        )
        self._all_plots["mc_pk_params"] = p.draw()
        fname = f"{self.sim_id}_mc_pk_params.svg"
        fpath = Path(save_dir, fname)
        p.save(fpath, verbose=False, width=width, height=height)

    @staticmethod
    def _calc_confint(df, quants=(0.025, 0.5, 0.975)):
        """Compute confidence/prediction intervals.

        :param df: dataframe, where each row contains concentration values as a
           function of time
        :param quants: iterable of quantile values for confidence interval
           calculations
        """
        p_interval = df.quantile(q=quants, axis=0)
        lower = p_interval.ix[quants[0], :]
        dep_var = p_interval.ix[quants[1], :]
        upper = p_interval.ix[quants[2], :]
        return lower, dep_var, upper


# ------------------------------------------------------------------------------


def analyze(
    mc_outfiles,
    sim_specs,
    plots_save_dir,
    stats_save_dir,
    label_with_sim_rnums=True,
    width=11,
    height=8.5,
):
    """Analyze Monte Carlo analysis output files and generate plots.

    :param mc_outfiles: iterable of MC output file paths
    :param sim_specs: path to the PoPKAT save file
    :param plots_save_dir: path to directory into which plot files should be
       saved
    :param label_with_sim_rnums: True: display output results (plots, etc.)
        with sim ids for labels, False: use data ids for labels
    """
    mca = MCAnalyzer(mc_outfiles, sim_specs, label_with_sim_rnums=label_with_sim_rnums)
    mca.plot(plots_save_dir, width=width, height=height)
    mca.calc_pk_params(stats_save_dir)
    results = {"plots": mca._all_plots, "tables": mca._all_tables}
    return results
