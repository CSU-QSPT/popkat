"""
.. module:: serializer
   :synopsis: Save, retrieve, and search for simulation data and results

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import itertools
import os
import shutil
import sqlite3
import tempfile
from collections import namedtuple
from pathlib import Path

from utils import gen_utils
from utils import db_utils
from utils.shared import SimInfo
from utils.db_utils import SimFile
from config.settings import SIM_DB_ASSOC_FILE_DIR, BACKUP_DIR_NAME

# =============================================================================
# Utility objects and classes
# =============================================================================


class All(object):
    pass


# =============================================================================
# Main class
# =============================================================================
class Serializer(object):
    """Class associated with saving, retrieving, and searching PoPKAT simulation
       results"""

    def __init__(self, save_file, storage_path=None, num_backups=4):
        """Specify the structure (schema) of the save file and create it if it doesn't
        already exist

        Args:
            save_file: desired full path for PoPKAT serialization file
            storage_path (str): location in which auxiliary files should be stored
        """
        # create the various data structures from the file specs
        db_specs, table_names, sim_file_cols = db_utils.db_specs()
        self._file_schema = [(_.name, _.db_type) for _ in db_specs]
        self._searchable_fields = [_.name for _ in db_specs if _.is_searchable]
        self._settable_fields = [_.name for _ in db_specs if _.is_settable]
        self._all_table_cols = [_.name for _ in db_specs]
        self._popkat_sim = namedtuple("popkat_sim", [_.name for _ in db_specs])
        self._table_names = table_names
        self._sim_file_cols = sim_file_cols
        # create the save file if needed
        self.save_file = save_file
        if not Path(save_file).is_file():
            self._create()
        # manage the path for storing auxiliary files
        if storage_path is None:
            fdir = Path(save_file).parent
            storage_path = fdir / SIM_DB_ASSOC_FILE_DIR
        storage_path.mkdir(exist_ok=True)
        self.storage_path = storage_path
        SimInfo.storage_path = storage_path
        self._num_backups = num_backups
        self._timestamp = gen_utils.timestamp()

    def _create(self):
        """Create the save file using the schema defined in the _db_specs method"""
        try:
            sf = sqlite3.connect(self.save_file, detect_types=sqlite3.PARSE_DECLTYPES)
        except sqlite3.OperationalError:
            raise Exception("Unable to create %s" % self.save_file)
        cursor = sf.cursor()
        fields = ", ".join(["%s %s" % (k, t) for (k, t) in self._file_schema])
        for tbl in self._table_names:
            create_cmd = "CREATE TABLE %s (%s);" % (tbl, fields)
            cursor.execute(create_cmd)
        sf.commit()
        cursor.close()
        sf.close()

    def add_simulation(
        self,
        table_name,
        input_files,
        env_file,
        model_exe,
        output_files,
        output_plots,
        output_tables,
        sim_id,
        sim_type,
        sim_params,
        model_params,
        dosing,
        pkdata,
        description=None,
        notes=None,
        tags=None,
        model_label=None,
        timestamp=None,
        other_info=None,
    ):
        """Add simulation data to the save file
        """
        if other_info is None:
            other_info = {}
        notes = notes or "PoPKAT simulation conducted on {self._timestamp}"
        description = description or "PoPKAT simulation"
        tags = tags or "simulation, drug"
        timestamp = timestamp or self._timestamp

        def _create_pkt(_files):
            _pkt = SimFile(_files, self.storage_path, create_archive=True)
            return _pkt

        sim_data = dict(
            input_files=_create_pkt(input_files),
            env_file=_create_pkt(env_file),
            model_exe=_create_pkt(model_exe),
            output_files=_create_pkt(output_files),
            output_plots=output_plots,
            output_tables=output_tables,
            timestamp=timestamp,
            sim_id=sim_id,
            sim_type=sim_type,
            description=description,
            notes=notes,
            tags=tags,
            model_label=model_label,
            other_info=other_info,
            sim_params=sim_params,
            model_params=model_params,
            dosing=dosing,
            pkdata=pkdata,
        )
        sf = sqlite3.connect(self.save_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = sf.cursor()
        fields = ", ".join(["%s" % name for name in self._settable_fields])
        keys = ", ".join([":%s" % name for name in self._settable_fields])
        insert_cmd = "INSERT INTO %s (%s) VALUES (%s)" % (table_name, fields, keys)
        cursor.execute(insert_cmd, sim_data)
        sf.commit()
        cursor.close()
        sf.close()

    def get_refs(self, cols, key=All):
        """Get the file references (hashes) for the specified columns and key"""
        scols = ",".join(gen_utils.to_list(cols))
        tables = ",".join(self._table_names)
        sf = sqlite3.connect(self.save_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = sf.cursor()
        if key is All:
            get_refs_cmd = "SELECT %s FROM %s" % (scols, tables)
        else:
            get_refs_cmd = "SELECT %s FROM %s WHERE key=%i" % (scols, tables, key)
        cursor.execute(get_refs_cmd)
        result = cursor.fetchall()
        # flatten and remove duplicates
        result_set = set(itertools.chain.from_iterable(result))
        sf.commit()
        cursor.close()
        sf.close()
        return result_set

    def delete_simulation(self, key, table):
        """Delete the simulation with the given database index key

        This method won't return an error if the key does not exists
        """
        sf = sqlite3.connect(self.save_file, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = sf.cursor()
        delete_cmd = "DELETE FROM %s WHERE key=%i" % (table, key)
        cursor.execute(delete_cmd)
        sf.commit()
        cursor.close()
        sf.close()

    def _delete_files(self, fnames, fpath):
        """Delete the specified files"""
        for fn in fnames:
            fpath = fpath / fn
            if fpath.exists():
                fpath.unlink()

    def get_simulations(self, key=None, sim_id=None, text=None):
        """Return simulations matching a certain sim_id or containing specified search
        text

        Args:
            key (int): database id
            sim_id (str): simulation id
            text (str): text used to locate records

        Note: choose only one of sim_id or text

        Returns:
            sims (list of namedtuples): simulations (input, output, etc.) satisfying
            search results
        """
        tables = list(self._table_names)

        def _namedtuple_factory(cursor, row):
            return self._popkat_sim(*row)

        if key and sim_id and text:
            raise ValueError(
                "Error: Specify one of key, sim_id, or search text, not both"
            )

        all_sims = []
        sf = sqlite3.connect(self.save_file, detect_types=sqlite3.PARSE_DECLTYPES)
        sf.row_factory = _namedtuple_factory
        cursor = sf.cursor()
        for table in tables:
            if text:
                cond = " OR ".join(
                    [
                        "%s LIKE '%s'" % (col, "%" + text + "%")
                        for col in self._searchable_fields
                    ]
                )
                search_cmd = "SELECT * FROM %s WHERE %s" % (table, cond)
                fmeth = "fetchall"
            if sim_id:
                search_cmd = "SELECT * FROM %s WHERE sim_id LIKE '%s'" % (
                    table,
                    "%" + sim_id + "%",
                )
                fmeth = "fetchone"
            if key:
                search_cmd = "SELECT * FROM %s WHERE key==%i" % (table, key)
                fmeth = "fetchone"
            cursor.execute(search_cmd)
            sims = getattr(cursor, fmeth)()
            if sims:
                if isinstance(sims, list):
                    all_sims.extend(sims)
                else:
                    all_sims.append(sims)
        cursor.close()
        sf.close()
        return all_sims

    def _get_contents(self, dfiles, store_externally=True):
        """Return the file contents or, if `store_externally` is True,
        return the file hash and save the file contents in compressed format

        Args:
            dfile (str): paths to files
            store_externally (bool): whether to store the file contents external to the
            save file

        Returns:
            contents: file contents or hash of file

        """
        dfiles = gen_utils.to_list(dfiles)
        if store_externally:
            outfile = gen_utils.concatenate(dfiles)
            fhash = gen_utils.hash_file(outfile)
            self._store_file(dfiles, fhash)
            # TODO: determine why the threading code below doesn't complete
            # ** Because the storage and compression may be time consuming,
            # ** spawn a thread for this task
            # ** using a daemon thread seems like the right approach, but has some
            # ** issues:
            # ** - no explicit monitoring or control of the thread
            # ** - the task may not complete if the main process is stopped
            # thread = threading.Thread(target=self._store_file,
            #                           args=(dfiles, contents))
            # thread.daemon = True
            # thread.start()
        else:
            contents = self._read_file_contents(dfiles)
        return contents

    def _backup_db_file(self):
        """Make a time-stamped copy of the database file and store it
        in a subdirectory of the directory in which the database file
        is stored

        TODO: We also need to store the the associated files
        """
        num_backups = self._num_backups
        timestamp = self._timestamp
        fdir = Path(self.save_file).parent
        backup_root = fdir / BACKUP_DIR_NAME
        dest_dir = backup_root / timestamp
        # copy storage tree to backup dir
        shutil.copytree(fdir, dest_dir, ignore=shutil.ignore_patterns("backups"))
        # keep only the specified number of backups
        bdirs = sorted(backup_root.glob("*/"), reverse=True)
        del_list = bdirs[num_backups:]
        for ddir in del_list:
            shutil.rmtree(ddir)

    def _read_file_contents(self, dfiles):
        """Read and return the contents of the specified file

        Args:
            dfiles (list): list of paths to files

        Returns:
            contents (str or bytes): the contents resulting from reading the specified
            file
        """
        fh, tfile = tempfile.mkstemp()
        tfile = gen_utils.concatenate(dfiles)
        with open(tfile, "r") as fh:
            contents = fh.read()
        return contents

    def clean_storage_dir(self):
        """Remove files from storage that are no longer referred to in
        the database"""
        db_refs = self.get_refs(self._sim_file_cols, key=All)
        fs_refs = set(os.listdir(self.storage_path))
        to_remove = fs_refs - db_refs
        for fl in to_remove:
            fpath = Path(self.storage_path) / fl
            fpath.unlink()
