---
title: Simulation Information
---

On this page, details of the simulation can be specified.


## General Information


Description
: A unique description for the simulation

Notes
: Details about the simulation

Tags
: A set of comma- or space-separated words that can be used in simulation
searches


## Simulation type

Forward
: A single model simulation using scalar values of the model parameters

Monte Carlo:
: A set of simulations using *distributions* specified for model parameters


Sensitivity
: A global sensitivity analysis using the model parameters specified

Parameter estimation + Setpoints
: A parameter estimation followed by an analysis using the estimated distributions


## Simulation details

The entries presented will depend on the simulation type.

The entire list is as follows:

Start time
: The start time for the simulations

End time
: The end time for the simulations


Number of time steps
: The number of time steps to record within the interval [Start time, End time]

Random seed
: The seed used to initialize the pseudo random number (PRN) generator. By using the same seed, simulations relying on PRNs can be repeated. If this entry is left blank, a seed based on the current system time will be used and stochastic simulation results can vary from run to run.

Number of draws
: For Monte Carlo simulations, the number of times the target distributions are sampled

Number of iterations
: The length of the chain for parameter estimation (Markov chain Monte Carlo) simulations
