"""
.. module:: pk
   :synopsis: Pharmacokinetic calculations associated with popkat analyses

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import numpy as np
import pandas as pd

DEF_NINTERP = 3


def calc_AUC(t, C, inf=False, ninterp=DEF_NINTERP):
    """Compute the AUC (area under the curve).

    :param t: array or list of time values
    :param C: array or list of concentration values
    :param ninterp: number of points to be used for extrapolation of the
       t/C curve
    """
    t, C = np.asarray(t), np.asarray(C)
    elim_rate_const = calc_elim_rate_const(t, C, ninterp=ninterp)
    AUC_tinf = (C[-1] / elim_rate_const) if inf else 0
    AUC = np.trapz(C, t) + AUC_tinf
    return AUC


def calc_mean_residence_time(t, C, ninterp=DEF_NINTERP):
    """Compute the mean residence time.

    :param t: array or list of time values
    :param C: array or list of concentration values
    :param ninterp: number of points to be used for extrapolation of the
       t/C curve
    """
    t, C = np.asarray(t), np.asarray(C)
    AUMC = np.trapz(C * t, t)
    AUC = calc_AUC(t, C, inf=False, ninterp=ninterp)
    MRT = AUMC / AUC
    return MRT


def calc_tmax(t, C):
    """Compute the time at which the maximum concentration occurs.

    :param t: array or list of time values
    :param C: array or list of concentration values
    :param ninterp: number of points to be used for extrapolation of the
       t/C curve
    """
    t, C = np.asarray(t), np.asarray(C)
    imax = np.argmax(C)
    tmax = t[imax]
    return tmax


def calc_cmax(t, C):
    """Compute the maximum concentration.

    :param t: array or list of time values
    :param C: array or list of concentration values
    :param ninterp: number of points to be used for extrapolation of the
       t/C curve
    """
    t, C = np.asarray(t), np.asarray(C)
    imax = np.argmax(C)
    Cmax = C[imax]
    return Cmax


def calc_elim_rate_const(t, C, ninterp=DEF_NINTERP):
    """Compute the elimination rate.

    :param t: array or list of time values
    :param C: array or list of concentration values
    :param ninterp: number of points to be used for extrapolation of the
       t/C curve
    """
    t, C = np.asarray(t), np.asarray(C)
    # eliminate 'bad' values
    inds = C > 0
    t, C = t[inds], C[inds]
    lnC = np.log(C)
    # linear fit to last points
    linear = 1
    slope, intercept = np.polyfit(t[-ninterp:], lnC[-ninterp:], linear)
    ke = -slope
    return ke


def calc_elim_half_life(t, C, ninterp=DEF_NINTERP):
    """Compute the elimination half life.

    :param t: array or list of time values
    :param C: array or list of concentration values
    :param ninterp: number of points to be used for extrapolation of the
       t/C curve
    """
    t, C = np.asarray(t), np.asarray(C)
    elim_rate_const = calc_elim_rate_const(t, C, ninterp=ninterp)
    thalf = np.log(2) / elim_rate_const
    return thalf


def calc_clearance(t, C, dose, ninterp=DEF_NINTERP):
    """Compute the clearance rate.

    :param t: array or list of time values
    :param C: array or list of concentration values
    :param dose: administered dose
    :param ninterp: number of points to be used for extrapolation of the
       t/C curve
    """
    t, C = np.asarray(t), np.asarray(C)
    AUC_inf = calc_AUC(t, C, inf=True, ninterp=ninterp)
    CL = dose / AUC_inf
    return CL


def calc_volume_of_distribution(t, C, dose, ninterp=DEF_NINTERP):
    """Compute the volume of distribution.

    :param t: array or list of time values
    :param C: array or list of concentration values
    :param dose: administered dose
    :param ninterp: number of points to be used for extrapolation of the
       t/C curve
    """
    t, C = np.asarray(t), np.asarray(C)
    ke = calc_elim_rate_const(t, C, ninterp=ninterp)
    CL = calc_clearance(t, C, dose, ninterp=ninterp)
    Vd = CL / ke
    return Vd


def calc_all_pk(t, C, dose=None, ninterp=DEF_NINTERP):
    """Compute all of the PK parameters.

    :param t: array or list of time values
    :param C: array or list of concentration values
    :param dose: administered dose
    :param ninterp: number of points to be used for extrapolation of the t/C curve
    """
    pk = {}
    pk["AUC"] = calc_AUC(t, C, ninterp=ninterp)
    pk["AUC_inf"] = calc_AUC(t, C, inf=True, ninterp=ninterp)
    pk["MRT"] = calc_mean_residence_time(t, C, ninterp=ninterp)
    pk["tmax"] = calc_tmax(t, C)
    pk["Cmax"] = calc_cmax(t, C)
    pk["kelim"] = calc_elim_rate_const(t, C, ninterp=ninterp)
    pk["t_half"] = calc_elim_half_life(t, C, ninterp=ninterp)
    if dose:
        pk["clearance"] = calc_clearance(t, C, dose, ninterp=ninterp)
        pk["volume_of_distribution"] = calc_volume_of_distribution(
            t, C, dose, ninterp=ninterp
        )
    return pk


def calc_pk_from_df(df, t, ninterp=DEF_NINTERP):
    """Calculate PK parameters based on a dataframe.

    :param t: array or list of time values
    :param C: array or list of concentration values
    :param dose: administered dose
    :param ninterp: number of points to be used for extrapolation of the
       t/C curve
    """
    pk_df = pd.DataFrame()
    fmap = {
        "AUC": lambda C: calc_AUC(t, C, ninterp=ninterp),
        "AUC_inf": lambda C: calc_AUC(t, C, inf=True, ninterp=ninterp),
        "MRT": lambda C: calc_mean_residence_time(t, C, ninterp=ninterp),
        "tmax": lambda C: calc_tmax(t, C),
        "Cmax": lambda C: calc_cmax(t, C),
        "kelim": lambda C: calc_elim_rate_const(t, C, ninterp=ninterp),
        "t_half": lambda C: calc_elim_half_life(t, C, ninterp=ninterp),
    }
    for pname, func in fmap.items():
        pk_df[pname] = df.apply(func, axis=1, raw=True)
    return pk_df
