"""
.. module:: mcmc
   :synopsis: Functionality to analyze the Markov chain Monte Carlo output from
              MCSim/PoPKAT simulations

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from pathlib import Path

import pandas as pd
from plotnine import aes, facet_wrap, geom_histogram, ggplot, labs

from utils import gen_utils
from config.settings import BAR_COLOR, LASTN_PTS, PLOT_THEME

from .popkatdata import PoPKATData


# ---------------------------------------------------------------------
# MCMC analysis
# ---------------------------------------------------------------------
class MCMCAnalyzer(object):
    """Produce plots and statistics related to Markov chain Monte Carlo
    analyses."""

    def __init__(
        self, SimInfo, mcmc_outfile, lastn_pts=LASTN_PTS, label_with_sim_rnums=True
    ):
        """Read an MCMC file into a dataframe

        :param mcmc_outfile: path to MCMC output file
        :param sim_specs: path to PoPKAT save file
        :param lastn_pts: number of points to use from the end of the
           chains (0=all)
        :param slabel_with_sim_rnums: True: use sim rnums, False: use data ids
        """
        self.label_with_sim_rnums = label_with_sim_rnums
        sim_specs = SimInfo.sim_specs
        self.sim_id = SimInfo.sim_id
        self._all_plots = {}
        self._all_tables = {}
        self._df = pd.read_csv(mcmc_outfile, sep="\t")
        self._param_df, self._pnames, self._pdata = self._parse_output(
            lastn_pts=lastn_pts
        )
        if sim_specs and not label_with_sim_rnums:
            pkd = PoPKATData(sim_specs)
            self._rename_id = pkd.sim_rnum_to_data_id
            self._id_map = pkd.id_map
        else:
            self._rename_id = gen_utils.no_op

    def _parse_output(self, lastn_pts=LASTN_PTS):
        """Parse the data from a dataframe containing MCMC results.

        :param lastn_pts: number of points to use from the end of the
           chains (0=all)
        """
        df = self._df
        pdata, pnames = {}, set()
        tidy_df, col_df = pd.DataFrame(), pd.DataFrame()
        colnames = df.columns.values.tolist()
        # retain column names that seem to represent parameter levels
        for c in colnames:
            name, level = gen_utils.extract_name_and_level(c, sim_type="mcmc")
            if name and level:
                pnames.add(name)
                dat = df[c][-lastn_pts:]
                ident = gen_utils.update_id(level)
                # the order of these column assignments is important
                col_df["value"] = dat
                col_df["param"] = name
                col_df["ident"] = ident
                tidy_df = tidy_df.append(col_df)
                pdata.setdefault(name, []).append((ident, dat))
        return tidy_df, list(pnames), pdata

    def plot(self, save_dir, width=11, height=8.5):
        """Plot parameter histograms.

        :param save_dir: directory into which plots should be saved
        :param width: width of plot in inches
        :param height: height of plot in inches
        """
        param_df = self._param_df
        for param in self._pnames:
            p_df = param_df[param_df.param == param]
            p = (
                ggplot()
                + geom_histogram(p_df, aes("value"), bins=20, fill=BAR_COLOR)
                + facet_wrap("~ ident", labeller=self._rename_id)
                + PLOT_THEME()
                + labs(y="Count", x=param, title=f"Variation in {param}")
            )
            self._all_plots[f"_mcmc_{param}"] = p.draw()
            fname = f"{self.sim_id}_mcmc_{param}.svg"
            fpath = Path(save_dir, fname)
            p.save(fpath, verbose=False, width=width, height=height)

    def calc_stats(self, save_dir):
        """Compute various summary statistics for the parameter distributions.

        :param save_dir: directory into which stat table should be saved
        """
        stats = {}
        sfuncs = ["mean", "min", "max", "var", "skew", "kurt"]
        for param, pdata in self._pdata.items():
            all_stats = {}
            for p, dat in pdata:
                pstats = {}
                for f in sfuncs:
                    pstats[f] = getattr(dat, f)()
                all_stats[p] = pstats
            astats = pd.DataFrame.from_dict(all_stats, orient="index")
            # rename to data ids
            if not self.label_with_sim_rnums:
                astats.index = astats.index.map(self._rename_id)
            stats[param] = astats
        for p, st in stats.items():
            self._all_tables[f"mcmc_{p}_stats"] = st.to_csv(
                path_or_buf=None, index=False
            )
            fname = f"{self.sim_id}_mcmc_{p}_stats.txt"
            fpath = Path(save_dir, fname)
            with open(fpath, "w") as fh:
                fh.write(st.to_csv(sep="\t", encoding="utf-8", float_format="%.4g"))
        return stats


# ------------------------------------------------------------------------------


def analyze(
    mcmc_outfile,
    plots_save_dir,
    stats_save_dir,
    sim_specs=None,
    lastn_pts=LASTN_PTS,
    label_with_sim_rnums=True,
    width=11,
    height=8.5,
):
    """Analyze a Markov chain Monte Carlo analysis output file and generate
    plots and statistics.

    :param mc_outfiles: iterable of MC output file paths
    :param plots_save_dir: path to directory into which plot files should be
       saved
    :param stats_save_dir: path to directory into which stats files should be
       saved
    :param lastn_pts: number of points to use from the end of the
       chains (0=all)
    :param label_with_sim_rnums: True: display output results (plots, etc.)
        with sim ids for labels, False: use data ids for labels
    """
    mcmca = MCMCAnalyzer(
        mcmc_outfile,
        sim_specs=sim_specs,
        label_with_sim_rnums=label_with_sim_rnums,
        lastn_pts=lastn_pts,
    )
    mcmca.plot(plots_save_dir, width=width, height=height)
    mcmca.calc_stats(stats_save_dir)
    results = {"plots": mcmca._all_plots, "tables": mcmca._all_tables}
    return results
