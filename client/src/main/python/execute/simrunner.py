"""
.. module:: simrunner
   :synopsis: Functionality to setup and run MCSim over the network using the package
              rpyc

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import json
import sys
from pathlib import Path
import shlex

import rpyc

from utils import gen_utils
from utils import shared
from config.consts import MsgDest

MSGS = {
    "COPYTO": "ST: Copying file '%s' from client to server...",
    "COPYFROM": "ST: Copying file '%s' from server to client...",
    "COPYWRK": "ST: Copying file '%s' to local work directory...",
    "NOCOPY": (
        "ST: Client and server storage location are the same. No copy will be done."
    ),
    "STARTSIM": "ST: Starting %s simulation...",
    "STOPSIM": "ST: Stopping %s simulation...",
}

SimInfo = shared.SimInfo()


class MCSimRunner(object):
    """Run MCSim on a remote server using remote procedure calls"""

    def __init__(self, conn, sock, sim_dirs, sim_type, msg_dest=MsgDest.SOCKET):
        self._conn = conn
        self._sock = sock
        self._sim_dirs = sim_dirs
        self._sim_type = sim_type
        self._proc = None
        self._outfile = None
        msg_dest_map = {
            MsgDest.SOCKET: self._sock.send,
            MsgDest.STDOUT: print,
            MsgDest.NULL: lambda x: None,
        }
        self._model_exe_map = self._map_label_to_basename()
        self._output = msg_dest_map[msg_dest]

    def copy_to_remote(self, infile):
        """Copy input file from local to remote"""
        infile = gen_utils.path_to_filename(infile)
        remote_work_dir = self._sim_dirs["remote_work_dir"]
        r_pathlib = self._conn.modules.pathlib
        localpath = self._sim_dirs["sim_infile_dir"] / infile
        remotepath = r_pathlib.PurePath(remote_work_dir, infile)
        msg = MSGS["COPYTO"] % infile
        self._output(msg.encode())
        rpyc.gen_utils.classic.upload(self._conn, localpath, remotepath)

    def copy_from_remote(self):
        """Copy output files from remote to local"""
        outfile = gen_utils.path_to_filename(self._outfile)
        remote_work_dir = self._sim_dirs["remote_work_dir"]
        r_pathlib = self._conn.modules.pathlib
        localpath = self._sim_dirs["sim_outfile_dir"] / outfile
        remotepath = r_pathlib.PurePath(remote_work_dir, outfile)
        msg = MSGS["COPYFROM"] % outfile
        self._output(msg.encode())
        rpyc.utils.classic.download(self._conn, remotepath, localpath)

    def _map_label_to_basename(self):
        """Retrieve the model index, and load info into the shared datastructure"""
        model_exe_dir = self._sim_dirs["models_dir"]
        model_exe_index = Path(model_exe_dir) / "index"
        model_exe_map = {}
        # parse index file and check to see if all model_exes exist
        with open(model_exe_index, "r") as fh:
            for line in fh:
                fields = shlex.split(line, comments=True)
                if fields:
                    label, name_in_fs, description = fields
                    fs_path = Path(model_exe_dir) / name_in_fs
                    if fs_path.is_file():
                        model_exe_map[label] = name_in_fs
                    else:
                        raise FileNotFoundError(f"Model file {fs_path} was not found.")
        return model_exe_map

    def _construct_cmd(self, model_label, infile, outfile, iter_freq=1):
        """Build the command to run on the remote"""
        # convert the label to the filesystem basename
        model = self._model_exe_map[model_label]
        model, infile, outfile = map(
            gen_utils.path_to_filename, (model, infile, outfile)
        )
        r_pathlib = self._conn.modules.pathlib
        remote_work_dir = self._sim_dirs["remote_work_dir"]
        models_dir = self._sim_dirs["remote_models_dir"]
        iter_flag = f"-i {iter_freq}" if iter_freq else ""
        # try to assure that the paths are appropriate for the OS
        # and that model, infile, and outfile are just filenames and not
        # full paths
        mod_path = r_pathlib.PurePath(models_dir, model)
        in_path = r_pathlib.PurePath(remote_work_dir, infile)
        out_path = r_pathlib.PurePath(remote_work_dir, outfile)
        cmd = [str(p) for p in (mod_path, iter_flag, in_path, out_path)]
        return cmd

    def get_environment(self, model_label):
        """Get the properties of the remote computing environment"""
        # convert the label to the filesystem basename
        model = self._model_exe_map[model_label]
        sim_id = SimInfo.sim_id
        outfile = f"{sim_id}.env"
        r_pathlib = self._conn.modules.pathlib
        models_dir = self._sim_dirs["remote_models_dir"]
        r_env = self._conn.modules.execution_environment
        mpath = r_pathlib.PurePath(models_dir, model)
        remote_env = r_env.get_env(mpath)
        localpath = self._sim_dirs["local_work_dir"] / outfile
        # the data structure returned from the remote process
        # is not compatible with json, so convert it
        r_env = dict(remote_env)
        with open(localpath, "w") as fh:
            json.dump(r_env, fh)
        return remote_env

    def run_sim(self, model_label, infile, outfile, iter_freq=1):
        """Connect to a remote machine using the rpyc package,
        send remote stdout to local stdout or to a socket."""
        # convert the label to the filesystem basename
        model = self._model_exe_map[model_label]
        rmodules = self._conn.modules
        cmd = self._construct_cmd(model, infile, outfile, iter_freq=iter_freq)
        self._outfile = outfile
        rmodules.sys.stdout = sys.stdout
        opts = dict(
            stdout=rmodules.subprocess.PIPE,
            shell=False,
            bufsize=1,
            universal_newlines=True,
        )
        msg = (MSGS["STARTSIM"] % self._sim_type).encode()
        self._output(msg)
        with rmodules.subprocess.Popen(cmd, **opts) as self._proc:
            rmodules.sys.stdout.flush()
            for line in self._proc.stdout:
                self._output(line.encode())
        if self._proc.returncode == 0:
            error = ()
        else:
            error = self._proc.returncode
        return error

    def terminate_on_remote(self):
        """Terminate the running process

        On windows 'terminate()' and 'kill()' are synonyms
        """
        msg = (MSGS["STOPSIM"] % self._sim_type).encode()
        self._output(msg)
        self._proc.terminate()
        self._proc.kill()


# ------------------------------------------------------------------------------


def clean_up_remote(conn, rdir):
    """Remove directory on the remote"""
    r_shutil = conn.modules.shutil
    r_shutil.rmtree(rdir)


def run_full_process(
    infile,
    outfile,
    model_label,
    conn,
    sock,
    sim_dirs,
    sim_type=None,
    msg_dest=MsgDest.SOCKET,
    iter_freq=1,
):
    """Run a full upload, execute, download, clean up sequence"""
    q = MCSimRunner(conn, sock, sim_dirs, sim_type, msg_dest=msg_dest)
    q.get_environment(model_label)
    q.copy_to_remote(infile)
    error = q.run_sim(model_label, infile, outfile, iter_freq=iter_freq)
    if error:
        err_msg = "Error in simulation: retcode={error}"
        raise gen_utils.PoPKATUtilsError(err_msg)
    else:
        q.copy_from_remote()
    del q
