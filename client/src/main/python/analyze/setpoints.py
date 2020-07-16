"""
.. module:: setpoints
   :synopsis: Functionality to analyze the SetPoints output from MCSim/PoPKAT
              simulations

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from .montecarlo import MCAnalyzer as SetPtsAnalyzer


def analyze(
    SimInfo,
    setpts_outfiles,
    plots_save_dir,
    stats_save_dir,
    label_with_sim_rnums=True,
    width=11,
    height=8.5,
):
    """Analyze SetPoints analysis output files and generate plots.

    :param setpts_outfiles: iterable of setpoints output file paths
    :param sim_specs: path to the PoPKAT save file
    :param plots_save_dir: path to directory into which plot files should be
       saved
    :param label_with_sim_rnums: True: display output results (plots, etc.)
        with sim ids for labels, False: use data ids for labels
    """
    setpts = SetPtsAnalyzer(
        SimInfo, setpts_outfiles, label_with_sim_rnums=label_with_sim_rnums
    )
    setpts.plot(plots_save_dir, width=width, height=height)
    setpts.calc_pk_params(stats_save_dir)
    results = {"plots": setpts._all_plots, "tables": setpts._all_tables}
    return results
