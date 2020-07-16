"""
.. module:: shared
   :synopsis: getters/setters and datastructures for info sharing across modules

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""


from config.consts import VALID_SIM_TYPES
from config.settings import MODEL_PARAM_SENSITIVITY, MODEL_PARAM_VARIABILITY


from utils import db_utils
from utils.gen_utils import PoPKATUtilsError

# ------------------------------------------------------------------------------
# storage classes
# ------------------------------------------------------------------------------


class SimInfo(object):
    """A Monostate (Borg) class to share state across instances.
    It is used as a container for various simulation settings and arguments
    """

    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state
        self._params_hash_file = None
        self._db_info = {"col_map": None, "databases": {}, "tables": {}}
        self._sim_specs = {
            "sim_geninfo": None,
            "sim_params": None,
            "model_params": None,
            "dosing": None,
            "pkdata": None,
            "model_param_variability": MODEL_PARAM_VARIABILITY,
            "model_param_sensitivity": MODEL_PARAM_SENSITIVITY,
            "meta_info": None,
        }
        self._sim_dirs = {
            "local_work_dir": None,
            "remote_work_dir": None,
            "log_dir": None,
            "models_dir": None,
        }
        self._output_plots = {}
        self._output_tables = {}

    # --------------------------------------------------------------------------------------
    # getters/setters related to constructing the main datastructure, sim_specs
    # --------------------------------------------------------------------------------------

    @property
    def sim_specs(self):
        return self._sim_specs

    @property
    def model_params(self):
        return self._model_params

    @model_params.setter
    def model_params(self, val):
        self._sim_specs["model_params"] = val
        self._model_params = val

    @property
    def dosing(self):
        return self._dosing

    @dosing.setter
    def dosing(self, val):
        self._sim_specs["dosing"] = val
        self._dosing = val

    @property
    def pkdata(self):
        return self._pkdata

    @pkdata.setter
    def pkdata(self, val):
        self._sim_specs["pkdata"] = val
        self._pkdata = val

    @property
    def sim_params(self):
        return self._sim_params

    @sim_params.setter
    def sim_params(self, val):
        self._sim_specs["sim_params"] = val
        self._sim_params = val

    @property
    def sim_type(self):
        return self._sim_params["sim_type"]

    @sim_type.setter
    def sim_type(self, val):
        if val not in VALID_SIM_TYPES:
            all_types = ", ".join([f"'{s}'" for s in VALID_SIM_TYPES])
            errmsg = (
                f"Improper simulation type: '{val}'. ",
                f"Valid types are as follows: {all_types}.",
            )
            raise PoPKATUtilsError(errmsg)
        self._sim_params["sim_type"] = val

    @property
    def sim_geninfo(self):
        return self._sim_geninfo

    @sim_geninfo.setter
    def sim_geninfo(self, val):
        self._sim_specs["sim_geninfo"] = val
        self._sim_geninfo = val

    @property
    def sim_id(self):
        return self._sim_geninfo["sim_id"]

    @property
    def meta_info(self):
        return self._meta_info

    @meta_info.setter
    def meta_info(self, val):
        self._sim_specs["meta_info"] = val
        self._meta_info = val

    @property
    def output_plots(self):
        return self._output_plots

    @output_plots.setter
    def output_plots(self, val):
        self._output_plots.update(val)

    @property
    def output_tables(self):
        return self._output_tables

    @output_tables.setter
    def output_tables(self, val):
        self._output_tables.update(val)

    @property
    def sim_files(self):
        return self._sim_files

    @sim_files.setter
    def sim_files(self, val):
        self._sim_files = val

    @property
    def model_exe_info(self):
        return self._model_exe_info

    @model_exe_info.setter
    def model_exe_info(self, val):
        self._model_exe_info = val

    # --------------------------------------------------------------------------------------
    # getters/setters related to running the simulation
    # --------------------------------------------------------------------------------------

    @property
    def num_samples(self):
        num_samples = self._sim_params["num_samples"]
        return num_samples

    @num_samples.setter
    def num_samples(self, val):
        self._sim_params["num_samples"] = val

    @property
    def model_label(self):
        return self._model_label

    @model_label.setter
    def model_label(self, val):
        self._model_label = val

    @property
    def sim_dirs(self):
        return self._sim_dirs

    @sim_dirs.setter
    def sim_dirs(self, val):
        self._sim_dirs = val

    @property
    def iter_freq(self):
        return self._iter_freq

    @iter_freq.setter
    def iter_freq(self, val):
        self._iter_freq = val

    @property
    def storage_path(self):
        return self._storage_path

    @storage_path.setter
    def storage_path(self, val):
        self._storage_path = val

    # --------------------------------------------------------------------------------------
    # getters/setters related to networking
    # --------------------------------------------------------------------------------------

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, val):
        self._host = val

    @property
    def sock(self):
        return self._sock

    @sock.setter
    def sock(self, val):
        self._sock = val

    @property
    def conn(self):
        return self._conn

    @conn.setter
    def conn(self, val):
        self._conn = val

    @property
    def msg_dest(self):
        return self._msg_dest

    @msg_dest.setter
    def msg_dest(self, val):
        self._msg_dest = val

    # --------------------------------------------------------------------------------------
    # getters/setters related to the database and db model
    # --------------------------------------------------------------------------------------

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, val):
        self._model = val

    @property
    def db_info(self):
        return self._db_info

    @db_info.setter
    def db_info(self, val):
        db_path, table_map = val
        if not self._db_info["col_map"]:
            table_name = list(table_map.values())[0]  # all tables have the same layout
            col_map = db_utils.map_db_cols(db_path, table_name)
            self._db_info["col_map"] = col_map
        # database
        db, cname = db_utils.connect_db(db_path)
        self._db_info["database"] = {"db": db, "cname": cname, "db_path": db_path}
        # tables
        for label, table in table_map.items():
            model = db_utils.create_db_model(db, table)
            self._db_info["tables"][label] = {"name": table, "model": model}
