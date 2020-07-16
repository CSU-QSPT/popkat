"""
.. module:: db_utils
   :synopsis: Utilities associated with the database

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import sqlite3
import tempfile
import random
import string
import zipfile
import pickle
import shutil
from pathlib import Path
from collections import namedtuple

from PyQt5.QtSql import QSqlDatabase, QSqlTableModel, QSqlQuery
from PyQt5.QtCore import QByteArray

from config.settings import (
    DB_TABLE_NAMES,
    NUM_BACKUPS_TO_KEEP,
    DB_PATH,
    BACKUP_DIR_NAME,
)
from utils import gen_utils
from config.settings import COMPRESSION_TYPE
from config.consts import VALID_COMPRESSION_TYPES


if COMPRESSION_TYPE not in VALID_COMPRESSION_TYPES:
    raise ValueError(f"Invalid compression type: {COMPRESSION_TYPE}")


# ------------------------------------------------------------------------------
# Utils related to PoPKAT objects
# ------------------------------------------------------------------------------


class SimFile:
    """Special type to handle files or file-derived info that are stored
    in the db"""

    def __init__(self, fpaths, storage_path, create_archive=False):
        fpaths = gen_utils.to_list(fpaths)
        concat_file = gen_utils.concatenate(fpaths)
        fhash = gen_utils.hash_file(concat_file)
        self._storage_path = storage_path
        self.finfo = f"{fhash}.{COMPRESSION_TYPE}"
        self._fpaths = fpaths
        self._concat_file = concat_file
        if create_archive:
            self._compress()

    def get_contents(self):
        cfile = self._concat_file
        with open(cfile, "r") as fh:
            contents = fh.read()
        return contents

    def _compress(self):
        cspec = VALID_COMPRESSION_TYPES[COMPRESSION_TYPE]
        fpaths = self._fpaths
        finfo = Path(self._storage_path) / self.finfo
        if not finfo.is_file():
            with zipfile.ZipFile(finfo, "w") as mzip:
                for fp in fpaths:
                    name = Path(fp).name
                    mzip.write(fp, arcname=name, compress_type=cspec)

    def _extract(self, path):
        finfo = Path(self._storage_path) / self.finfo
        with zipfile.ZipFile(finfo, "r") as arc:
            arc.extractall(path=path)

    def __repr__(self):
        return f"{self.__class__} (loc={str(self.finfo)})"


# ------------------------------------------------------------------------------
# utility functions
# ------------------------------------------------------------------------------


def db_fname_to_pkt(finfo):
    storage_path = Path(gen_utils.SimInfo.storage_path)
    temp_path = Path(tempfile.mkdtemp(prefix="pkt_"))
    fpath = storage_path / finfo
    with zipfile.ZipFile(fpath, "r") as fh:
        nlist = fh.namelist()
        fh.extractall(path=temp_path)
    fpaths = [temp_path.joinpath(_name) for _name in nlist]
    result = SimFile(fpaths, temp_path)
    return result


def create_db_model(db, table_name):
    model = QSqlTableModel(None, db)
    model.setTable(table_name)
    model.select()
    return model


def random_token(num_chars=10):
    chars = string.ascii_letters + string.digits
    token = "".join(random.choice(chars) for i in range(num_chars))
    return token


def connect_db(db_path):
    """ """
    db = QSqlDatabase.addDatabase("QSQLITE", random_token())
    db.setDatabaseName(db_path)
    cname = db.connectionName()
    db.open()
    return db, cname


def clean_up_db(db, model, cname):
    del model
    db.close()
    del db
    QSqlDatabase.removeDatabase(cname)


def map_db_cols(dbname, tablename):
    conn = sqlite3.connect(dbname)
    c = conn.cursor()
    c.execute(f"select * from {tablename}")
    col_map = dict([(desc[0], ind) for ind, desc in enumerate(c.description)])
    conn.close()
    return col_map


def delete_duplicate_rows(db, table):
    all_cols = set([fs.name for fs in TABLE_SCHEMA])
    ignore_cols = set(["key", "sim_id", "timestamp"])
    cols_to_group_on = ",".join(list(all_cols - ignore_cols))
    cmd = f"""DELETE FROM {table}
    WHERE key NOT IN (SELECT MIN(key)
    FROM {table} GROUP BY {cols_to_group_on})"""
    QSqlQuery(cmd, db)


def copy_record(
    db, src_table, dest_table, sim_id, new_sim_id, timestamp, new_timestamp
):
    # use the sim_id as the basis for the lookup and update
    query = QSqlQuery(db)
    cmds = [
        f"""CREATE TEMPORARY TABLE temp_table AS SELECT * FROM {src_table} WHERE
            sim_id = :sim_id""",
        f"UPDATE temp_table SET sim_id = :new_sim_id",
        f"UPDATE temp_table SET timestamp = :new_timestamp",
        f"UPDATE temp_table SET key = NULL",
        f"INSERT INTO {dest_table} SELECT * FROM temp_table",
        f"DROP TABLE temp_table",
    ]
    for cmd in cmds:
        query.prepare(cmd)
        query.bindValue(":sim_id", sim_id)
        query.bindValue(":new_sim_id", new_sim_id)
        query.bindValue(":new_timestamp", new_timestamp)
        query.exec_()


def update_record(db, table_name, sim_id, update_map):
    """Update the columns of a record
    Use the sim_id as the basis for the lookup and update"""
    query = QSqlQuery(db)
    for col, val in update_map.items():
        value = preprocess_value(col, val)
        query.prepare(f"UPDATE {table_name} SET {col} = :value WHERE sim_id = :sim_id")
        query.bindValue(":value", value)
        query.bindValue(":sim_id", sim_id)
        query.exec_()


def preprocess_value(col, val, special=("BLOB",)):
    COL_VALS_TO_PREPROCESS = [fs.name for fs in TABLE_SCHEMA if fs.db_type in special]
    if col in COL_VALS_TO_PREPROCESS:
        result = QByteArray(pickle.dumps(val))
    else:
        result = val
    return result


def backup_db_file(save_file=DB_PATH):
    """Make a time-stamped copy of the database file and store it
    in a subdirectory of the directory in which the database file
    is stored

    TODO: We also need to store the the associated files
    """
    num_backups = NUM_BACKUPS_TO_KEEP
    timestamp = gen_utils.timestamp()
    fdir = Path(save_file).parent
    backup_root = fdir / BACKUP_DIR_NAME
    dest_dir = backup_root / timestamp
    # copy storage tree to backup dir
    shutil.copytree(fdir, dest_dir, ignore=shutil.ignore_patterns("backups"))
    # keep only the specified number of backups
    bdirs = sorted(backup_root.glob("*/"), reverse=True)
    del_list = bdirs[num_backups:]
    for ddir in del_list:
        shutil.rmtree(ddir)


# ------------------------------------------------------------------------------
# Database schema and properties
# ------------------------------------------------------------------------------


def db_specs():
    """Specify the structure and characteristics for the save file table and fields"""
    table_names = DB_TABLE_NAMES.values()
    row_spec = namedtuple(
        "row_spec", ["name", "db_type", "is_searchable", "is_settable"]
    )
    sim_file_cols = ["input_files", "env_file", "model_exe", "output_files"]
    sim_file_specs = [row_spec(_sf, "SIMFILE", False, True) for _sf in sim_file_cols]
    sim_specs = [
        row_spec("key", "INTEGER PRIMARY KEY", True, False),
        row_spec("description", "TEXT", True, True),
        row_spec("notes", "TEXT", True, True),
        row_spec("timestamp", "TEXT", True, True),
        row_spec("sim_id", "TEXT", True, True),
        row_spec("sim_type", "TEXT", True, True),
        row_spec("tags", "TEXT", True, True),
        row_spec("model_label", "TEXT", True, True),
        row_spec("sim_params", "BLOB", False, True),
        row_spec("model_params", "BLOB", False, True),
        row_spec("dosing", "BLOB", False, True),
        row_spec("pkdata", "BLOB", False, True),
        row_spec("output_plots", "BLOB", False, True),
        row_spec("output_tables", "BLOB", False, True),
        row_spec("other_info", "BLOB", False, True),
    ]
    file_specs = sim_specs + sim_file_specs
    return file_specs, table_names, sim_file_cols


# ------------------------------------------------------------------------------
# Database adapters and converters
# ------------------------------------------------------------------------------


def adapt_pktfile(simfile):
    return str(simfile.finfo)


def convert_pktfile(finfo):
    return finfo.decode("utf-8")


# register the adapter and converter
sqlite3.register_adapter(SimFile, adapt_pktfile)
sqlite3.register_converter("SIMFILE", convert_pktfile)

# ------------------------------------------------------------------------------
# precalculated some quantities
# ------------------------------------------------------------------------------

TABLE_SCHEMA, _, _ = db_specs()
