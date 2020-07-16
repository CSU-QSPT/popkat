"""
.. module:: workflows
   :synopsis: Workflows for the various types of popkat analyses

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""


import glob
import warnings

import analyze.forward as forward
import analyze.mcmc as mcmc
import analyze.montecarlo as montecarlo
import analyze.sensitivity as sensitivity
import analyze.setpoints as setpoints
import execute.convert as convert
import execute.simrunner as simrunner
from execute import simdirs
from utils import gen_utils
from utils import shared
from config.settings import LASTN_PTS
from config.consts import MsgDest, VALID_SIM_TYPES

SimInfo = shared.SimInfo()

warnings.simplefilter("ignore", UserWarning)

# ------------------------------------------------------------------------------


def _convert_file(setpts_data_file=None, run_id=""):
    """Convert popkat file to mcsim input file"""
    sim_specs = SimInfo.sim_specs
    sim_type = SimInfo.sim_type
    sim_dirs = SimInfo.sim_dirs
    sim_infile_dir = sim_dirs["sim_infile_dir"]
    sim_outfile_dir = sim_dirs["sim_outfile_dir"]
    sim_infile, sim_outfile = convert.to_mcsim_input(
        sim_specs,
        sim_infile_dir,
        sim_outfile_dir,
        setpts_data_file=setpts_data_file,
        sim_type=sim_type,
        run_id=run_id,
    )
    return sim_infile, sim_outfile


def _connect_to_server():
    conn, sock = gen_utils.connect()
    SimInfo.conn = conn
    SimInfo.sock = sock


def _create_simdirs():
    conn = SimInfo.conn
    simdirs.create_local_dirs()
    simdirs.create_remote_dirs(conn)


def _run_sim(sim_infile, sim_outfile):
    """Run the simulation"""
    simrunner.run_full_process(
        sim_infile,
        sim_outfile,
        SimInfo.gen_info["model_label"],
        SimInfo.conn,
        SimInfo.sock,
        SimInfo.sim_dirs,
        sim_type=SimInfo.sim_type,
        msg_dest=SimInfo.msg_dest,
        iter_freq=SimInfo.iter_freq,
    )


# ------------------------------------------------------------------------------


def fwd_analysis(sim_type="fwd"):
    """Conduct a Forward (fwd) analysis"""
    SimInfo.sim_type = sim_type
    sim_plots_dir = SimInfo.sim_dirs["sim_plots_dir"]
    sim_tables_dir = SimInfo.sim_dirs["sim_tables_dir"]
    # convert the popkat file to mcsim input file
    sim_infile, sim_outfile = _convert_file()
    # run the simulation, including file transfers
    _run_sim(sim_infile, sim_outfile)
    results = forward.analyze(SimInfo, sim_outfile, sim_plots_dir, sim_tables_dir)
    return results


# ------------------------------------------------------------------------------


def mc_analysis(sim_type="mc"):
    """Conduct a Monte Carlo analysis"""
    SimInfo.sim_type = sim_type
    sim_plots_dir = SimInfo.sim_dirs["sim_plots_dir"]
    sim_tables_dir = SimInfo.sim_dirs["sim_tables_dir"]
    # convert the popkat file to mcsim input file
    sim_infile, sim_outfile = _convert_file()
    # run the simulation, including file transfers
    _run_sim(sim_infile, sim_outfile)
    # analyze the output
    mc_outfiles = gen_utils.to_list(sim_outfile)
    results = montecarlo.analyze(
        SimInfo, mc_outfiles, sim_plots_dir, sim_tables_dir, label_with_sim_rnums=True
    )
    return results


# ------------------------------------------------------------------------------


def mcmc_analysis(sim_type="mcmc"):
    """Conduct a Markov chain Monte Carlo analysis"""
    SimInfo.sim_type = sim_type
    sim_plots_dir = SimInfo.sim_dirs["sim_plots_dir"]
    sim_tables_dir = SimInfo.sim_dirs["sim_tables_dir"]
    sim_posteriors_dir = SimInfo.sim_dirs["sim_posteriors_dir"]
    # convert the popkat file to mcsim input file
    sim_infile, sim_outfile = _convert_file()
    # run the simulation, including file transfers
    _run_sim(sim_infile, sim_outfile)
    # analyze results
    results = mcmc.analyze(
        SimInfo,
        sim_outfile,
        sim_plots_dir,
        sim_tables_dir,
        lastn_pts=LASTN_PTS,
        label_with_sim_rnums=True,
    )
    # split output into setpt files
    sim_id = SimInfo.sim_id
    gen_utils.split_mcmc_posteriors(
        sim_outfile, sim_posteriors_dir, lastn_pts=LASTN_PTS, basename=sim_id
    )
    return results


# ------------------------------------------------------------------------------


def setpts_analysis(sim_type="setpts"):
    """Conduct a SetPoints (setpt) analysis"""
    SimInfo.sim_type = sim_type
    # create setpt input files
    sim_infiles, sim_outfiles = [], []
    sim_posteriors_dir = SimInfo.sim_dirs["sim_posteriors_dir"]
    sim_plots_dir = SimInfo.sim_dirs["sim_plots_dir"]
    sim_tables_dir = SimInfo.sim_dirs["sim_tables_dir"]
    # convert the popkat file to mcsim input file
    fpath = f"{sim_posteriors_dir}/*.txt"
    for sp_file in glob.glob(fpath):
        run_id = gen_utils.get_run_id(sp_file)
        sim_infile, sim_outfile = _convert_file(setpts_data_file=sp_file, run_id=run_id)
        sim_infiles.append(sim_infile)
        sim_outfiles.append(sim_outfile)
        # run the simulation, including file transfers
        _run_sim(sim_infile, sim_outfile)
    # analyze the output
    setpts_outfiles = gen_utils.to_list(sim_outfiles)
    results = setpoints.analyze(
        SimInfo,
        setpts_outfiles,
        sim_plots_dir,
        sim_tables_dir,
        label_with_sim_rnums=True,
    )
    return results


# ------------------------------------------------------------------------------


def sens_analysis(sim_type="sens"):
    """Conduct a sensitivity analysis using SALib and MCSim"""
    SimInfo.sim_type = sim_type
    sim_infile_dir = SimInfo.sim_dirs["sim_infile_dir"]
    sim_tables_dir = SimInfo.sim_dirs["sim_tables_dir"]
    sim_plots_dir = SimInfo.sim_dirs["sim_plots_dir"]
    sim_id = SimInfo.sim_id
    sp_datfile = sim_infile_dir / f"{sim_id}_sens.in"
    sim_infile, sim_outfile = _convert_file(setpts_data_file=sp_datfile)
    ssa = sensitivity.SensitivityAnalysis(
        SimInfo, sim_infile, sp_datfile, method="sobol", num_samples=SimInfo.num_samples
    )
    ssa.write_samples()
    _run_sim(sim_infile, sim_outfile)
    results = sensitivity.analyze(
        ssa, sim_outfile, sim_plots_dir, sim_tables_dir, width=11, height=8.5
    )
    return results


# ------------------------------------------------------------------------------


def run_workflow(
    sim_specs,
    model,
    msg_dest=MsgDest.SOCKET,
    do_cleanup=True,
    iter_freq=1,
    storage_path=None,
):
    """Perform all steps in a PoPKAT analysis"""

    SimInfo.iter_freq = iter_freq
    SimInfo.msg_dest = msg_dest

    # connect to sim server and create sim dirs
    _connect_to_server()
    _create_simdirs()

    # initialize data structures
    all_sim_types = VALID_SIM_TYPES
    base_sim_types = [x for x in all_sim_types if "+" not in x]
    wf_mapper = {}  # map sim type to analysis function
    for stype in base_sim_types:
        func_name = f"{stype}_analysis"
        wf_mapper[stype] = globals()[func_name]

    # call the function that is specific for the type of analysis
    # a plus sign represents a combination of analyses, e.g., mcmc+setpts is
    # an mcmc analysis followed by a setpts analysis
    sim_type = SimInfo.sim_type
    sims = [s.strip() for s in sim_type.split("+")]
    for sim in sims:
        results = wf_mapper[sim](sim_type=sim)

    # # clean up remote and close connection
    # if do_cleanup:
    #     simrunner.clean_up_remote(conn, sim_dirs["remote_work_dir"])
    # conn.close()
    return results
