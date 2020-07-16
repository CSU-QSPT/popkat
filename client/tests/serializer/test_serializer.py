import os
import sys
import pickle
from pprint import pprint
import random
import glob

join = os.path.join
script_path = os.path.dirname(os.path.realpath(__file__))
sys.path.extend(
    [
        f"{script_path}/../../src/main",
        f"{script_path}/../../src/main/python/execute",
        f"{script_path}/../../src/main/python/utils",
        f"{script_path}/../../src/main/python/config",
    ]
)

import python
from config import consts

import serializer
from consts import DEFAULT_SAVE_FILE_NAME, DEFAULT_SAVE_FILE_SUFFIX, SIM_FILE_SUFFIXES
import db_utils


class WordList(object):
    def __init__(self, fpath):
        with open(fpath, "rt") as fh:
            self._word_list = [_.strip() for _ in fh.readlines()]

    def get_random_phrase(self, num_to_select=5):
        sample = random.sample(self._word_list, num_to_select)
        wstring = " ".join(sample)
        return wstring


wpath = join(script_path, "tests/data/common_words.txt")
wl = WordList(wpath)

sim_dir = join(script_path, "tests", "MCSim_examples", "MC")

# specify the files to be serialized and the save file
save_file = join(
    script_path,
    "tests",
    "output",
    f"{DEFAULT_SAVE_FILE_NAME}.{DEFAULT_SAVE_FILE_SUFFIX}",
)

params_file = join(sim_dir, "four_cmpt.params")
# this file is already a pickle dump of a dictionary
with open(params_file, "rb") as fh:
    _params = pickle.load(fh)
model_params = pickle.dumps(_params["model_params"])

input_files = glob.glob(f"{sim_dir}/*.{SIM_FILE_SUFFIXES['input_file']}")
env_file = glob.glob(f"{sim_dir}/*.{SIM_FILE_SUFFIXES['env_file']}")
model_exe = glob.glob(f"{sim_dir}/*.{SIM_FILE_SUFFIXES['model_exe']}")
output_files = glob.glob(f"{sim_dir}/*.{SIM_FILE_SUFFIXES['output_file']}")

plot_pickle = os.path.join(
    script_path, "../../src/main/python/gui/test_data/ggplt.pickle"
)
table_file = os.path.join(
    script_path, "../../src/main/python/gui/test_data/test_pkdata.csv"
)

dosing_file = os.path.join(
    script_path, "../../src/main/python/gui/test_data/dosing.pickle"
)

pkdata_file = os.path.join(
    script_path, "../../src/main/python/gui/test_data/pkdata.pickle"
)


with open(plot_pickle, "rb") as fh:
    sp = pickle.load(fh)
output_plots = pickle.dumps(sp)

with open(table_file, "r") as fi:
    table_data = fi.read()
st = {"Table 1": table_data, "Table 2": table_data, "Table 3": table_data}
output_tables = pickle.dumps(st)

with open(dosing_file, "rb") as fh:
    sdo = pickle.load(fh)
dosing = pickle.dumps(sdo)

with open(pkdata_file, "rb") as fh:
    spk = pickle.load(fh)
pkdata = pickle.dumps(spk)

srl = serializer.Serializer(save_file)

sim_types = ["mc", "mcmc", "sens", "setpts", "fwd"]
model_labels = ["acat_2cpt", "acat_2cpt_pop", "model_01", "model_02"]


def generate_sim_id(bits=160):
    return hex(random.getrandbits(bits))[2:]


# fill the file with a few simulations
for tname in ["mysims", "samples"]:
    for num_sims in range(20):
        # simulation data
        # description = 'Four compartment model simulation v2'
        description = wl.get_random_phrase(5)
        notes = wl.get_random_phrase(20)
        tags = ",".join(wl.get_random_phrase(3).split())
        sim_id = generate_sim_id()
        sim_type = random.choice(sim_types)
        model_label = random.choice(model_labels)

        sim_params_dict = {
            "sim_type": f"{sim_type}",
            "num_iters": random.randrange(5000, 50000),
            "num_draws": random.randrange(1000, 5000),
            "num_samples": random.randrange(1000, 10000),
            "t_start": 0,
            "t_end": random.randrange(2, 96),
            "t_step": random.randrange(1, 100) / 10.0,
            "rng_seed": random.randrange(1, 10000),
            "rtol": 0.000001,
            "atol": 0.000001,
        }
        sim_params = pickle.dumps(sim_params_dict)

        # other potentially useful information
        other_info_raw = dict(
            username=wl.get_random_phrase(2), project=wl.get_random_phrase(3)
        )
        other_info = pickle.dumps(other_info_raw)

        # save the data

        srl.add_simulation(
            tname,
            input_files=input_files,
            env_file=env_file,
            model_exe=model_exe,
            output_files=output_files,
            output_plots=output_plots,
            output_tables=output_tables,
            sim_id=sim_id,
            sim_type=sim_type,
            sim_params=sim_params,
            model_params=model_params,
            dosing=dosing,
            pkdata=pkdata,
            description=description,
            notes=notes,
            model_label=model_label,
            tags=tags,
            timestamp=None,
            other_info=other_info,
        )

srl._backup_db_file()

# get a simulation by its key
# s = srl.get_simulations(sim_id="e5ae50ee-bd55-498d-a824-10963919af50")
# if s is not None:
#     r = s.sim_params
#     print("---", r)
#     rr = pickle.loads(r)
#     print("+++", rr)

# get sims by a search term (or fragment)
search_term = "seven"
sims = srl.get_simulations(text=search_term)
for s in sims:
    print(s.description)

# sim_id = '7be72f1a-9581-41fe-bbcc-d51a646f33e2'
# new_sim_id = '0000000000'
# srl.copy_simulation(sim_id, new_sim_id)

# delete a simulation
srl.delete_simulation(key=2, table="mysims")

# delete unneeded files from filesystem
# srl.clean_storage_dir()
