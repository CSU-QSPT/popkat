---
title: Dosing and Pharmacokinetic Data
---


## Data grid

For simulations involving *Parameter estimation*, a full grid will be presented into which dosing and pharmacokinetic data may be entered for multiple subjects. For other types of simulations, a simpler grid for entering dosing specifications will be used.

Thus, depending on the type of simulation, not all of the elements described below will be present in this interface page.

### Grid values

*Dosing type* should take on one of several integer values:

| Value |         Meaning         |
| :---: | :---------------------- |
|   0   | Oral: slow release      |
|   1   | Oral: immediate release |
|   2   | Intravenous             |

### Types of values

Aside from the *Dosing type*, values may be integers or floating point numbers.

The following columns can accept lists of values:
"Dose administration times", "Administered dose amounts", "Measurement time points"
and "Measured concentrations".

 Numerical values in these lists can be separated by commas, semicolons, spaces, or tabs.


## Edit table

Add Row
: Add a row to the bottom of the grid

Remove Row
: Delete the selected row

Remove All Rows
: Remove all the grid rows

## Load/Save

Load Data
: Fill the grid by selecting an appropriately-formatted comma-separated value (csv) file

Save Data
: Save the grid data to a csv file
