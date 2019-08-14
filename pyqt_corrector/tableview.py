from PySide2.QtWidgets import QTableView
from PySide2.QtCore import Signal, QItemSelection, QModelIndex


class TableView(QTableView):

    setCurrentIndexSignal = Signal(QModelIndex)

    def setCurrentIndex(self, index):
        self.setCurrentIndexSignal.emit(index)
        super().setCurrentIndex(index)
