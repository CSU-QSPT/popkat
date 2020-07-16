"""
.. module:: popkatdata
   :synopsis: Functionality to manipulate the data contained in a popkat save file

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

from collections import OrderedDict

from utils import shared, gen_utils
from config.consts import POPULATION_KEYWORD

SimInfo = shared.SimInfo()


class PoPKATData(object):
    """Read and parse PoPKAT file"""

    def __init__(self, sim_specs):
        self.pkdata = sim_specs["pkdata"]
        self.sim_params = sim_specs["sim_params"]
        self.id_map = self._create_id_mapping(add_pop=True)
        self.rev_id_map = {v: k for k, v in self.id_map.items()}

    def sim_rnum_to_data_id(self, sim_rnum):
        """Convert a simulation id into a pk data id

        :param sim_rnum: simulation run number (e.g., 's02')
        """
        if self.pkdata:
            data_id = self.id_map[sim_rnum]
        else:
            data_id = sim_rnum
        return data_id

    def data_id_to_sim_rnum(self, data_id):
        """Convert a data id to a simulation run number

        :param data_id: pk data subject id (e.g., 'jh')
        """
        if self.pkdata:
            sim_rnum = self.rev_id_map[data_id]
        else:
            sim_rnum = data_id
        return sim_rnum

    def _create_id_mapping(self, add_pop=True):
        """Create a list of ids from the datasets"""
        id_map = OrderedDict()
        data_ids = sorted(list(self.pkdata.keys()))
        sim_rnum = [gen_utils.update_id(f".{i}") for i in range(1, len(data_ids) + 1)]
        id_map = dict(zip(sim_rnum, data_ids))
        if add_pop:
            id_map[f"{POPULATION_KEYWORD}"] = POPULATION_KEYWORD
        return id_map
