import matplotlib as mpl
from PySide2.QtWidgets import QTabWidget, QWidget
from PySide2.QtCore import QModelIndex, Signal, Slot
from PySide2.QtGui import QColor


class Tab(QWidget):

    def __init__(self, filename, parent=None):
        super().__init__(parent)

        self.filename = filename


class TabWidget(QTabWidget):

    cellClickedSignal = Signal(int, QModelIndex, int, QModelIndex)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.previousCellIndex = QModelIndex()
        self.previousTabIndex = -1

    def filename(self, index):
        return self.widget(index).filename

    def filenames(self):
        for i in range(self.count()):
            yield self.widget(i).filename

    def getCurrentTableView(self):
        return self.currentWidget().children()[1]

    def getCurrentSelectedCell(self):
        if self.count() > 0:
            return self.getCurrentTableView().currentIndex()

        return QModelIndex()

    def setCurrentSelectedCell(self, index):
        if index.isValid():
            self.getCurrentTableView().setCurrentIndex(index)

    def getTableModel(self, index):
        return self.widget(index).children()[1].model()

    def getTableView(self, index):
        return self.widget(index).children()[1]

    def getCurrentTableModel(self):
        return self.getCurrentTableView().model()

    def models(self):
        for i in range(self.count()):
            yield self.getTableModel(i)

    def views(self):
        for i in range(self.count()):
            yield self.getTableView(i)

    def labelSet(self, index=-1):
        if index >= 0:
            return self.getTableModel(index).labelSet()

        labels = set()
        for model in self.models():
            labels |= model.labelSet()
        return labels

    def pageDatas(self, page):
        return [model.pageData(page) for model in self.models()]

    def color_map(self, tabIndex):
        labels = list(self.labelSet())
        labels.sort()
        num_colors = len(labels) + self.count() - 1
        colors = [
            QColor(x["color"])
            for i, x in zip(range(num_colors),
                            mpl.rcParams["axes.prop_cycle"])]
        curIndex = self.currentIndex()
        for i in range(self.count()):
            if i == curIndex:
                color_map = {
                    label: color for label, color in zip(labels, colors)}
            else:
                num_colors -= 1
                color_map = {label: colors[num_colors] for label in labels}
            if i == tabIndex:
                return color_map
        return None

    def getTableViewIndex(self, view):
        return [v for v in self.views()].index(view)

    @Slot(QModelIndex)
    def cellIndexChanged(self, index: QModelIndex):
        self.previousCellIndex = index

    @Slot(QModelIndex)
    def cellClicked(self, index: QModelIndex):
        tabIndex = self.getTableViewIndex(self.sender())
        self.cellClickedSignal.emit(
            tabIndex, index, self.previousTabIndex, self.previousCellIndex)
        self.previousCellIndex = index
        self.previousTabIndex = tabIndex
