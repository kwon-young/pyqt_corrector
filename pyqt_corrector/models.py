"""
File: models.py
Author: Kwon-Young Choi
Email: kwon-young.choi@hotmail.fr
Date: 2019-08-05
Description: Implement qt data models.
"""

from PySide2.QtCore import QModelIndex, QAbstractTableModel
from PySide2.QtCore import Qt, QRectF


def box2QRect(box):
    x1, y1, x2, y2 = [int(coord) for coord in box.split("x")]
    width, height = x2 - x1, y2 - y1
    return QRectF(x1, y1, width, height)


class TableModel(QAbstractTableModel):

    """Table Model"""

    def __init__(self, parent=None):
        """Constructor

        :data: table data
        :parent: parent widget

        """
        super().__init__(parent)

        self._parent = parent
        self._data = None

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
            page = self._data.iloc[index.row()][0]
            tableData = self._data.query(f"page == '{page}'").copy()
            tableData["box"] = tableData["box"].apply(box2QRect)
            return tableData
        return None

    def headerData(self, section, orientation, role):
        """Get header at given section"""
        if self._data is None:
            return None

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._data.columns[section]
            elif orientation == Qt.Vertical:
                return section
        return None

    def update(self, data):
        self._data = data
