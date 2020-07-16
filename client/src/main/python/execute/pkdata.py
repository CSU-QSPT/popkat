"""
.. module:: pkdata
   :synopsis: Functionality to parse various pk data table formats

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""


class PKData(object):
    """Base class for pk data parsing"""

    def init(self, data_file):
        with open(data_file, "r") as fh:
            self._data = fh.read()

    def parse(self):
        pass


class NONMEMPKData(PKData):
    """Functionality to parse a NONMEM data file"""

    def init(self, data_file):
        super().__init__(data_file)

    def parse(self):
        pass


class ExcelPKData(PKData):
    """Functionality to parse an excel spreadsheet data file"""

    def init(self, data_file):
        super().__init__(data_file)

    def parse(self):
        pass


class CSVPKData(PKData):
    """Functionality to parse a csv data file"""

    def init(self, data_file, sep="\t"):
        super().__init__(data_file)

    def parse(self):
        pass
