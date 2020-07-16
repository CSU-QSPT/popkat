# PoPKAT Design Notes

Last update: 20190821

- The guiding strategy for the gui application is not to have the conventional `open` and `save` functions, but instead have the user choose an existing simulation (could include a *blank*) from their previous simulations or a list of samples simulations.

- When a simulation is chosen, a new `sim_id` is generated, even if the user has no intention of changing anything. Culling the identical simulations will be done on startup or shutdown using something like `dbutils.delete_duplicate_rows`.

- Though not implemented yet, if a user changes a *meaningful* input, the simulation results (if present) are removed.

- The build system is `fbs`. The tutorial is [here](https://github.com/mherrmann/fbs-tutorial) and the code is [here](https://github.com/mherrmann/fbs). Using this system has necessitated minor changes to the file `main.py` to include the necessary hooks into the `fbs` machinery.
