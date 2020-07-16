"""
.. module:: utils
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import operator
from functools import reduce
import random

from PyQt5.QtCore import QSortFilterProxyModel
from PyQt5.QtGui import QValidator


from utils import gen_utils


def getFromDict(dataDict, mapList):
    return reduce(operator.getitem, mapList, dataDict)


def setInDict(dataDict, mapList, value):
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value


def generate_sim_id(bits=160):
    s_id = hex(random.getrandbits(bits))[2:]  # remove the hex prefix
    return s_id


class SortFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        QSortFilterProxyModel.__init__(self, *args, **kwargs)
        self.filters = {}

    def setFilterByColumn(self, regex, column):
        self.filters[column] = regex
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        for key, regex in self.filters.items():
            ix = self.sourceModel().index(source_row, key, source_parent)
            if ix.isValid():
                text = self.sourceModel().data(ix).toString()
                if not text.contains(regex):
                    return False
        return True


# ------------------------------------------------------------------------------
# Validators
# ------------------------------------------------------------------------------


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


class ValidateNumOrDist(QValidator):
    def __init__(self, parent=None):
        super().__init__(parent)

    def validate(self, arg, pos):
        is_valid = False
        is_valid_num = is_number(arg)

        # list the valid types of distributions and the potential args
        # test for is_valid_dist
        dists = gen_utils.get_known_dists()

        is_valid = is_valid_num or is_valid_dist

        if is_valid:
            validity = (QValidator.Acceptable, pos)
        else:
            validity = (QValidator.Invalid, pos)

        return validity


class ValidateBoolean(QValidator):
    def __init__(self, parent=None):
        super().__init__(parent)

    def validate(self, arg, pos):
        if int(arg) in [0, 1]:
            validity = (QValidator.Acceptable, arg, pos)
        else:
            validity = (QValidator.Invalid, arg, pos)
        return validity


class ValidateNotBlank(QValidator):
    def __init__(self, parent=None):
        super().__init__(parent)

    def validate(self, arg, pos):
        if len(arg) > 1:
            validity = (QValidator.Acceptable, arg, pos)
        else:
            validity = (QValidator.Invalid, arg, pos)
        return validity


def color_validity_state(cls, *args, **kwargs):
    sender = cls.sender()
    validator = sender.validator()
    state = validator.validate(sender.text(), 0)[0]
    if state == QValidator.Acceptable:
        color = "#c4df9b"  # green
    elif state == QValidator.Intermediate:
        color = "#fff79a"  # yellow
    else:
        color = "#f6989d"  # red
    sender.setStyleSheet("QLineEdit { background-color: %s }" % color)


# reg_ex = QRegularExpression("[a-zA-Z ]+")
# input_validator = QRegularExpressionValidator(reg_ex, ledit)
# ledit.setValidator(input_validator)
