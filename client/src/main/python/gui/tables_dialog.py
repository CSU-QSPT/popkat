"""
.. module:: tables_dialog
   :synopsis:

.. moduleauthor:: Brad Reisfeld <brad.reisfeld@colostate.edu>
"""

import csv

import pandas as pd

from PyQt5.QtWidgets import (
    QTableView,
    QVBoxLayout,
    QDialogButtonBox,
    QFileDialog,
    QDialog,
    QAbstractItemView,
)
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import (
    Qt,
    QAbstractTableModel,
    pyqtSlot,
    pyqtProperty,
    QVariant,
    QModelIndex,
)

from utils import shared

SimInfo = shared.SimInfo()


class TablesDialog(QDialog):
    def __init__(self, title, table, parent=None, *args):
        super().__init__(parent, *args)
        self._title = title
        self._table = table
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        tablelines = self._table.split()
        header, tabledata = tablelines[0].split(","), tablelines[1:]

        self.tableresults_view = QTableView(self)
        self.tableresults_model = QStandardItemModel(self)
        self.tableresults_view.setModel(self.tableresults_model)
        self.tableresults_model.setHorizontalHeaderLabels(header)
        # no editing allowed
        self.tableresults_view.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.tableresults_view)

        self.load_data(tabledata)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.setWindowTitle(f"PoPKAT: {self._title}")
        self.show()

    def load_data(self, data):
        model = self.tableresults_model
        reader = csv.reader(data)
        for row in reader:
            items = [QStandardItem(field) for field in row]
            model.appendRow(items)

    def save_data(self):
        fpath = None
        options = QFileDialog.Options() | QFileDialog.DontUseNativeDialog
        fpath, _ = QFileDialog.getSaveFileName(
            self, "Save data", "", "PK Datasets (*.csv)", options=options
        )
        if fpath:
            self.write_csv(fpath)

    def write_csv(self, fileName):
        model = self.pkdata_model
        with open(fileName, "w") as fileOutput:
            writer = csv.writer(fileOutput)
            writer.writerow(self._pkdata_fields)
            for rowNumber in range(model.rowCount()):
                fields = [
                    model.data(model.index(rowNumber, columnNumber), Qt.DisplayRole)
                    for columnNumber in range(model.columnCount())
                ]
                writer.writerow(fields)


# --------------------------------------------------------------------------------------
# A model based on a pandas dataframe
# from https://stackoverflow.com/a/44605011/11918518
# --------------------------------------------------------------------------------------


class DataFrameModel(QAbstractTableModel):
    DtypeRole = Qt.UserRole + 1000
    ValueRole = Qt.UserRole + 1001

    def __init__(self, df=pd.DataFrame(), parent=None):
        super(DataFrameModel, self).__init__(parent)
        self._dataframe = df

    def setDataFrame(self, dataframe):
        self.beginResetModel()
        self._dataframe = dataframe.copy()
        self.endResetModel()

    def dataFrame(self):
        return self._dataframe

    dataFrame = pyqtProperty(pd.DataFrame, fget=dataFrame, fset=setDataFrame)

    @pyqtSlot(int, Qt.Orientation, result=str)
    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._dataframe.columns[section]
            else:
                return str(self._dataframe.index[section])
        return QVariant()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._dataframe.index)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return self._dataframe.columns.size

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (
            0 <= index.row() < self.rowCount()
            and 0 <= index.column() < self.columnCount()
        ):
            return QVariant()
        row = self._dataframe.index[index.row()]
        col = self._dataframe.columns[index.column()]
        dt = self._dataframe[col].dtype

        val = self._dataframe.iloc[row][col]
        if role == Qt.DisplayRole:
            return str(val)
        elif role == DataFrameModel.ValueRole:
            return val
        if role == DataFrameModel.DtypeRole:
            return dt
        return QVariant()

    def roleNames(self):
        roles = {
            Qt.DisplayRole: b"display",
            DataFrameModel.DtypeRole: b"dtype",
            DataFrameModel.ValueRole: b"value",
        }
        return roles


# def btn_clk(self):
#     path = self.lineEdit.text()
#     df = pd.read_csv(path)
#     model = PandasModel(df)
#     self.tableView.setModel(model)
