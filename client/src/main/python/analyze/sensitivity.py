"""
.. module:: sensitivity
   :synopsis: Functionality to conduct a global sensitivity analysis

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import itertools
from importlib import import_module
from pathlib import Path

import pandas as pd
from plotnine import (
    aes,
    element_text,
    facet_wrap,
    geom_bar,
    geom_tile,
    ggplot,
    labs,
    scale_color_gradient2,
    scale_fill_discrete,
    scale_fill_gradient,
    scale_fill_gradientn,
    scale_fill_manual,
    theme,
    theme_bw,
)

from config.settings import PLOT_THEME, SA_METHOD
from config.consts import PROBLEM_MARKER, SA_LIB_METHODS

from .setpoints import SetPtsAnalyzer


class SensitivityAnalysis(object):
    """Conduct a sensitivity analysis

    This relies on the workflow for the SALib package:
    - generate sampling points
    - run function (setpoints analysis)
    - analyze function output

    Details about SALib - Sensitivity Analysis Library in Python are
    given here:
    - general info: https://salib.readthedocs.io/en/latest/index.html
    - API: https://salib.readthedocs.io/en/latest/api.html
    """

    def __init__(
        self, SimInfo, setpts_file, setpts_datfile, method=SA_METHOD, num_samples=1000
    ):
        sampler, analyzer = SA_LIB_METHODS[method]
        self._sampler = import_module(f".{sampler}", "SALib.sample")
        self._analyzer = import_module(f".{analyzer}", "SALib.analyze")
        self._setpts_file = setpts_file
        self._setpts_datfile = setpts_datfile
        self.sim_id = SimInfo.sim_id
        self._sim_specs = SimInfo.sim_specs
        self._problem = self._extract_problem()
        self._num_samples = num_samples
        self._sa_results = {}
        self._all_plots = {}
        self._all_tables = {}

    def _extract_problem(self):
        """Extract the SALib 'problem' from the setpoints file, which is stored
        in a specially-marked section of the file"""
        # a special comment marker that must be identical to the one
        # used in `mcsim_sens_file_template.j2`
        marker = PROBLEM_MARKER
        sfile = self._setpts_file
        plines = []
        with open(sfile, "r") as fh:
            for l in fh:
                if l.startswith(marker):
                    plines.append(l.lstrip(marker).strip())
        problem = eval("\n".join(plines))
        return problem

    def write_samples(self):
        """Generate the sample points and write them to a file
        in the format acceptable for a setpoints analysis
        """
        problem, num_samples = self._problem, self._num_samples
        param_values = self._sampler.sample(self._problem, num_samples)
        p = pd.DataFrame(param_values, columns=problem["names"])
        p.index = range(1, len(p) + 1)
        p.to_csv(self._setpts_datfile, sep="\t")

    def calc_sensitivity(self, setpts_outfile):
        """Conduct the actual sensitivity analysis, returning pandas
        dataframes as results

        S1: 1 x nvars array of main effects
        ST: 1 x nvars array of total effects
        S2: nvars x nvars array of interactions
        """
        sim_specs = self._sim_specs

        def _combinations(nparam):
            return itertools.combinations(range(nparam), 2)

        setpts = SetPtsAnalyzer(setpts_outfile, sim_specs)
        pk_params = setpts._pk_params_raw
        pk_params.drop(["ident"], inplace=True, axis=1)
        mparams = self._problem["names"]
        num_mparams = len(mparams)
        sa_main = pd.DataFrame()
        sa_interact = pd.DataFrame()
        for i, cname in enumerate(pk_params):
            si_vals = pd.DataFrame()
            Y = pk_params[cname].values
            Si = self._analyzer.analyze(self._problem, Y)
            interactions = Si["S2"]
            # create a tidy dataframe containing all of the results
            # main and total effect
            for si_ in ["S1", "ST"]:
                si_vals["value"] = Si[si_]
                si_vals["sens_level"] = si_
                si_vals["pk_param"] = cname
                si_vals["model_param"] = mparams
                sa_main = sa_main.append(si_vals)
            # interactions
            si_vals = pd.DataFrame()
            names = [(mparams[i], mparams[j]) for i, j in _combinations(num_mparams)]
            vals = [interactions[i, j] for i, j in _combinations(num_mparams)]
            n1, n2 = list(zip(*names))
            si_vals["value"] = vals
            si_vals["sens_level"] = "S2"
            si_vals["pk_param"] = cname
            si_vals["model_param_1"] = n1
            si_vals["model_param_2"] = n2
            sa_interact = sa_interact.append(si_vals)
        # as a result of the appends, we need to reset the main indices
        sa_main.reset_index(drop=True, inplace=True)
        sa_interact.reset_index(drop=True, inplace=True)
        self._sa_results["main"] = sa_main
        self._sa_results["interactions"] = sa_interact

    def write_results(self, save_dir):
        """Write the sensitivity analysis dataframe(s) to a file"""
        sim_id = self.sim_id
        for stype in ["main", "interactions"]:
            fname = save_dir / f"{sim_id}_sens_{stype}.txt"
            self._sa_results[stype].to_csv(fname, sep="\t")

    def plot(self, save_dir, width=11, height=8.5):
        """Generate various plots"""
        self._plot_main_effects(save_dir, width=width, height=height)
        self._plot_interactions(save_dir, width=width, height=height)

    def _plot_main_effects(self, save_dir, width=11, height=8.5):
        """Generate bar plots of the main effects"""
        cb_palette = (
            "#999999",
            "#56B4E9",
            "#E69F00",
            "#009E73",
            "#F0E442",
            "#0072B2",
            "#D55E00",
            "#CC79A7",
        )
        p_df = self._sa_results["main"]
        p = (
            ggplot(p_df, aes(x="model_param", y="value", fill="sens_level"))
            + geom_bar(stat="identity", position="dodge")
            + scale_fill_discrete(colors=cb_palette)
            + facet_wrap("~ pk_param")
            + PLOT_THEME()
            + theme(axis_text_x=element_text(angle=45, vjust=1, hjust=1))
            + labs(x="Model parameter", y="Value", title="Sensitivity: Main effects")
        )
        self._all_plots[f"sens_main"] = p.draw()
        fname = f"{self.sim_id}_sens_main.svg"
        fpath = Path(save_dir, fname)
        p.save(fpath, verbose=False, width=width, height=height)

    def _plot_interactions(self, save_dir, width=11, height=8.5):
        """Generate heatmap plots of the interaction effects"""
        cb_palette = ("#3794bf", "#FFFFFF", "#df8640")
        p_df = self._sa_results["interactions"]
        p = (
            ggplot(p_df, aes("model_param_1", "model_param_2", fill="value"))
            + geom_tile(aes(width=0.95, height=0.95))
            + facet_wrap("~ pk_param")
            + PLOT_THEME()
            + theme(axis_text_x=element_text(angle=45, vjust=1, hjust=1))
            + scale_fill_gradientn(colors=cb_palette)
            + labs(
                x="Model parameter 1",
                y="Model parameter 2",
                title="Sensitivity: Interactions",
            )
        )
        self._all_plots[f"sens_interact"] = p.draw()
        fname = f"{self.sim_id}_sens_interact.svg"
        fpath = Path(save_dir, fname)
        p.save(fpath, verbose=False, width=width, height=height)


# ------------------------------------------------------------------------------


def analyze(
    sa_object, setpts_outfile, plots_save_dir, stats_save_dir, width=11, height=8.5
):
    """Analyze sensitivity analysis output files and generate plots.

    :param mc_outfiles: iterable of MC output file paths
    :param sim_specs: path to the PoPKAT save file
    :param plots_save_dir: path to directory into which plot files should be
       saved
    """
    sa_object.calc_sensitivity(setpts_outfile)
    sa_object.plot(plots_save_dir, width=width, height=height)
    sa_object.write_results(stats_save_dir)
    results = {"plots": sa_object._all_plots, "tables": sa_object._all_tables}
    return results
