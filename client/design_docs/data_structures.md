# Key Data Structures and Database Information

## Data structures

**sim_geninfo**: python `dict`
- not stored directly in the database, but derivable
- keys: sim_id, description, notes, tags, timestamp
- stored in SimInfo

**sim_params**: python `dict`
- keys: sim_type, t_start, t_end, t_step, rng_seed, num_draws, num_iters
- stored in SimInfo

**model_params**: python `dict`
- stored in database in pickled format
- keys: 'Anatomical', 'Physiological', 'Drug', 'Drug Release', 'Drug:Tissue', 'Compartmental'

**pkdata**: python `dict`
- stored in database in pickled format

**dosing**: python `dict`
- stored in database in pickled format

**sim_spec**: python `dict`
- a * merging* of several component dictionaries:

```python
sim_specs = {
    "sim_params": sim_params,
    "sim_geninfo": sim_geninfo,
    "model_params": model_params,
    "dosing": dosing,
    "pkdata": pkdata,
    "model_param_variability": model_param_variability,
    "model_param_sensitivity": model_param_sensitivity,
    "meta_info": meta_info,
}
```


**dosing**: python `dict`
- keys: dosing_type, dose_amounts, dosing_times


**model_param_variability**: python `dict`
- keys: cv_ind, cv_pop
- default as config.MODEL_PARAM_VARIABILITY

**model_param_sensitivity**: python `dict`
- keys: low_factor, high_factor
- default value is defined as `utils.config.MODEL_PARAM_SENSITIVITY`


**meta_info**: python `dict`
Not used at present


## Database information

fields:
   - key
   - description
   - notes
   - timestamp
   - sim_id
   - tags
   - other_info
   - sim_params
   - model_params
   - model_exe
   - input_files
   - output_plots
   - output_tables
   - output_files
   - env_file
