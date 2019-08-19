"""
File: tablemodel.py
Author: Kwon-Young Choi
Email: kwon-young.choi@hotmail.fr
Date: 2019-08-05
Description: Implement qt data models.
"""
import pandas as pd
from PySide2.QtCore import QModelIndex, QAbstractTableModel, Qt, QRectF


def box2QRect(box):
    x1, y1, x2, y2 = [int(coord) for coord in box.split("x")]
    width, height = x2 - x1, y2 - y1
    return QRectF(x1, y1, width, height)


def QRectF2Box(rect):
    [x1, y1, x2, y2] = [int(coor) for coor in [
        rect.left(), rect.top(), rect.right(), rect.bottom()]]
    return f"{x1}x{y1}x{x2}x{y2}"


def openDataset(filename):
    dataset = pd.read_csv(
        filename, header=0, skipinitialspace=True, skip_blank_lines=True,
        comment="#")
    for i, col in enumerate(["page", "label", "box"]):
        assert dataset.columns[i] == col, \
            f"{filename} does not have column {col} at index {i}"
    return dataset


class TableModel(QAbstractTableModel):

    """Table Model"""

    def __init__(self, name, data, parent=None):
        """Constructor

        :data: table data
        :parent: parent widget

        """
        super().__init__(parent)

        self._data = data
        self.name = name

    def __str__(self):
        return f"TableModel<{self.name}>: {self._data.shape}"

    def rowCount(self, parent: QModelIndex):
        """Get the number of rows"""
        if self._data is None:
            return 0

        if not parent.isValid():
            return self._data.shape[0]
        return 0

    def columnCount(self, parent: QModelIndex):
        """Get the number of columns"""
        if self._data is None:
            return 0

        if not parent.isValid():
            return self._data.shape[1]
        return 0

    def data(self, index: QModelIndex, role):
        """Get data at given index"""
        if not index.isValid():
            return None

        if self._data is None:
            return None

        if role == Qt.DisplayRole:
            return self._data.iloc[index.row()][index.column()]
        if role == Qt.UserRole:
            page = self._data["page"][index.row()]
            tableData = self._data.query(f"page == '{page}'").copy()
            tableData["box"] = tableData["box"].apply(box2QRect)
            return tableData
        return None

    def rowAtIndex(self, row):
        if not row >= 0:
            return None

        if self._data is None:
            return None

        return self._data.iloc[row]

    def pageAtIndex(self, index: QModelIndex):
        if not index.isValid():
            return None

        if self._data is None:
            return None

        return self._data["page"][index.row()]

    def boxAtIndex(self, index: QModelIndex):
        if not index.isValid():
            return None

        if self._data is None:
            return None

        return box2QRect(self._data["box"][index.row()])

    def labelAtIndex(self, index: QModelIndex):
        if not index.isValid():
            return None

        if self._data is None:
            return None

        return self._data["label"][index.row()]


    def pageData(self, page):
        if self._data is None:
            return None
        tableData = self._data.query(f"page == '{page}'").copy()
        tableData["box"] = tableData["box"].apply(box2QRect)
        return tableData

    def headerData(self, section, orientation, role):
        """Get header at given section"""
        if self._data is None:
            return None

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._data.columns[section]
            if orientation == Qt.Vertical:
                return section
        return None

    def setData(self, index: QModelIndex, value, role):
        """Set data at given index"""
        if not index.isValid():
            return False

        if self._data is None:
            return False

        if role == Qt.EditRole:
            if index.column() == 0:
                raise "First column of dataset is not editable"
            if index.column() == 1:
                self._data.iloc[index.row(), index.column()] = value
                assert self._data.iloc[index.row()][index.column()] == value
                self.dataChanged.emit(index, index, role)
            if index.column() == 2:
                self._data.iloc[index.row(), index.column()] = QRectF2Box(
                    value)
                assert self._data.iloc[index.row()][index.column()] == \
                    QRectF2Box(value)
                self.dataChanged.emit(index, index, role)
                return True
        return False

    def setLabel(self, row, label):
        index = self.index(row, 1)
        return self.setData(index, label, Qt.EditRole)

    def makeRowData(self, page, label, box):
        return pd.Series([page, label, QRectF2Box(box)],
                         index=self._data.columns)

    def appendRow(self, rowData):
        if self._data is None:
            return False

        self._data = self._data.append(rowData, ignore_index=True)
        self._data = self._data.reset_index(drop=True)
        topLeft = self.index(self.rowCount(QModelIndex()), 0)
        bottomRight = self.index(self.rowCount(QModelIndex()),
                                 self.columnCount(QModelIndex()))
        self.layoutChanged.emit()
        self.dataChanged.emit(topLeft, bottomRight, Qt.EditRole)
        return True

    def deleteRow(self, row):
        if self._data is None:
            return False

        self._data = self._data.drop(row)
        self._data = self._data.reset_index(drop=True)
        topLeft = self.index(row, 0)
        bottomRight = self.index(row, self.columnCount(QModelIndex()))
        self.layoutChanged.emit()
        self.dataChanged.emit(topLeft, bottomRight, Qt.EditRole)
        return True

    def insertRow(self, row, rowData):
        dfA = self._data.iloc[:row]
        dfB = self._data.iloc[row:]
        self._data = dfA.append(rowData).append(dfB).reset_index(drop=True)
        topLeft = self.index(row, 0)
        bottomRight = self.index(row, self.columnCount(QModelIndex()))
        self.layoutChanged.emit()
        self.dataChanged.emit(topLeft, bottomRight, Qt.EditRole)

    def labelSet(self):
        return set(self._data["label"].unique())

    def save(self, name):
        self._data.to_csv(name, index=False)
