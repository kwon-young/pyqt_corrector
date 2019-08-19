import os
import glob
from PySide2.QtWidgets import QUndoCommand, QComboBox, QGridLayout, \
    QLabel
from PySide2.QtCore import QModelIndex, QMarginsF, Qt
from PySide2.QtGui import QPixmap
from pyqt_corrector.tablemodel import TableModel, openDataset
from pyqt_corrector.tableview import TableView
from pyqt_corrector.tabwidget import TabWidget, Tab
from pyqt_corrector.graphicsscene import GraphicsScene
from pyqt_corrector.graphicsitem import ResizableRect
from pyqt_corrector.smoothview import SmoothView


class DeleteDatasetCommand(QUndoCommand):

    """ Delete datasets from memory.
    This action will:
    * delete corresponding tab, tableview, tablemodel from memory,
    * remove tableview clicked signal connection,
    * remove corresponding elements from graphicsScene,
    * remove superfluous labels from the comboBox,
    * update remaining boxes color and tab indices to reflect the new state.
    If the current tab was deleted, this action is considered as a standard
    change of tab, like when cliking on another tab with the mouse.
    Therefore, it will not change the current viewport nor the current
    selected cell nor the background image nor the current page of the
    graphicsScene.
    When undoing, this action will:
    * restore corresponding tab, tableview, tablemodel at the same tab indices
      by rereading the corresponding dataset file,
    * add missing labels to the comboBox,
    * add deleted items to the graphicsScene and update tab indices,
    * update boxes color to reflect the new state,
    * restore previously selected tab and cell,
    * restore previous viewport.
    """

    def __init__(self, tabIndices, tabWidget, comboBox, graphicsView,
                 graphicsScene, parent=None):
        super().__init__(parent)
        self.tabIndices = tabIndices
        self.tabWidget: TabWidget = tabWidget
        self.comboBox: QComboBox = comboBox
        self.graphicsView: SmoothView = graphicsView
        self.graphicsScene: GraphicsScene = graphicsScene
        self.tabs = []
        self.deletedFilenames = []
        self.deletedItems = []
        self.index_map = {}
        self.previousSelectedTabIndex = self.tabWidget.currentIndex()
        self.previousSelectedCell = self.tabWidget.getCurrentSelectedCell()
        self.previousSceneRect = self.graphicsView.mapToScene(
            graphicsView.viewport().geometry()).boundingRect()

    def undo(self):
        for tab, tabIndex in zip(self.tabs, self.tabIndices):
            name = os.path.basename(tab.filename)
            self.tabWidget.insertTab(tabIndex, tab, name)
            # print("insert", tabIndex, self.tabIndices, self.tabWidget.count())
            self.tabWidget.getTableView(tabIndex).clicked.connect(
                self.tabWidget.cellClicked)

        self.comboBox.blockSignals(True)
        for label in self.tabWidget.labelSet():
            if self.comboBox.findText(label) == -1:
                self.comboBox.addItem(label)
        self.comboBox.blockSignals(False)

        reverse_index_map = {
            value: key for key, value in self.index_map.items()}
        self.graphicsScene.changeTabIndices(reverse_index_map)

        for item in self.deletedItems:
            self.graphicsScene.addItem(item)

        self.tabWidget.setCurrentIndex(self.previousSelectedTabIndex)
        self.tabWidget.previousTabIndex = self.previousSelectedTabIndex
        cellIndex = self.tabWidget.getCurrentTableModel().index(
            self.previousSelectedCell.row(),
            self.previousSelectedCell.column())
        self.tabWidget.setCurrentSelectedCell(cellIndex)
        self.graphicsView.fitInView(self.previousSceneRect)
        self.graphicsView.setFocus()

        for tabIndex in range(self.tabWidget.count()):
            self.graphicsScene.changeTabColor(
                tabIndex, self.tabWidget.color_map(tabIndex))

        self.setText(f"Open {self.deletedFilenames}")

    def redo(self):
        labelToRemove = set()
        labelToKeep = set()
        self.tabs = []
        self.deletedFilenames = []
        index_map = {}
        for tabIndex in range(self.tabWidget.count()):
            tab = self.tabWidget.widget(tabIndex)
            if tabIndex in self.tabIndices:
                labelToRemove |= set(self.tabWidget.labelSet(tabIndex))
                self.tabs.append(tab)
                self.deletedFilenames.append(tab.filename)
                self.deletedItems = self.graphicsScene.removeTabItems(tabIndex)
            else:
                labelToKeep |= set(self.tabWidget.labelSet(tabIndex))
                index_map[tabIndex] = tab

        for tab in self.tabs:
            tabIndex = self.tabWidget.indexOf(tab)
            view = self.tabWidget.getTableView(tabIndex)
            view.clicked.disconnect()
            # print("delete", tabIndex, self.tabIndices, self.tabWidget.count())
            self.tabWidget.removeTab(tabIndex)

        labelToRemove = [label for label in labelToRemove
                         if label not in labelToKeep]
        self.comboBox.blockSignals(True)
        for label in labelToRemove:
            index = self.comboBox.findText(label)
            self.comboBox.removeItem(index)
        self.comboBox.blockSignals(False)

        if self.tabWidget.count() > 0:
            self.index_map = {oldIndex: self.tabWidget.indexOf(tab)
                              for oldIndex, tab in index_map.items()}
            self.graphicsScene.changeTabIndices(self.index_map)
            for tabIndex in range(self.tabWidget.count()):
                self.graphicsScene.changeTabColor(
                    tabIndex, self.tabWidget.color_map(tabIndex))

        self.setText(f"Close {self.deletedFilenames}")


class OpenDatasetCommand(QUndoCommand):

    """ Open new csv dataset files.
    This command can open multiple csv dataset files,
    creates corresponding number of tab, table view and table model,
    select the first element of the first created tab,
    update combobox showing the current label,
    update graphicsScene with the current page and all boxes in that page,
    update graphicsView to center around the current box.
    Undoing action will completely undo all of the previous actions,
    including destroying the dataset, freeing memory and reset the state to
    the previous state.
    """

    def __init__(self, filenames, tabWidget, comboBox, graphicsScene,
                 messageLabel, parent=None):
        super().__init__(parent)
        self.filenames = filenames
        self.tabWidget: TabWidget = tabWidget
        self.comboBox: QComboBox = comboBox
        self.graphicsScene: GraphicsScene = graphicsScene
        self.messageLabel: QLabel = messageLabel
        self.tabIndices = []
        self.addedLabels = []

    def undo(self):
        tabs = [self.tabWidget.widget(tabIndex)
                for tabIndex in self.tabIndices]
        for tab in tabs:
            tabIndex = self.tabWidget.indexOf(tab)
            view = self.tabWidget.getTableView(tabIndex)
            view.clicked.disconnect()
            # print("delete", tabIndex, self.tabIndices, self.tabWidget.count())
            self.tabWidget.removeTab(tabIndex)
            tab.deleteLater()
        self.tabIndices = []

        self.comboBox.blockSignals(True)
        for label in self.addedLabels:
            index = self.comboBox.findText(label)
            self.comboBox.removeItem(index)
        self.addedLabels = []

        self.comboBox.blockSignals(False)

    def redo(self):
        """ Open csv datasets from filenames.
        This function will update the tabWidget with different tabs, comboBox and GraphicsScene.
        The GraphicsScene is updated completely by first removing all items and then
        redrawing the page + all boxes belonging to the page.
        Previous page and boxes are saved in the constructor.
        """
        for filename in self.filenames:
            try:
                dataset = openDataset(filename)
            except AssertionError as error:
                self.messageLabel.setText(str(error))
                continue

            tab = Tab(filename)
            name = os.path.basename(filename)
            self.tabWidget.addTab(tab, name)
            self.tabIndices.append(self.tabWidget.indexOf(tab))
            # print("append", self.tabIndices[-1], self.tabIndices, self.tabWidget.count())

            layout = QGridLayout(tab)

            view = TableView(tab)
            view.clicked.connect(self.tabWidget.cellClicked)
            view.setCurrentIndexSignal.connect(self.tabWidget.cellIndexChanged)
            layout.addWidget(view, 0, 0, 1, 1)

            model = TableModel(name, dataset, view)
            view.setModel(model)
            view.resizeColumnsToContents()
            width = view.verticalHeader().width() + 20
            for col in range(view.model().columnCount(QModelIndex())):
                width += view.columnWidth(col)
            view.setMinimumWidth(width)

        self.comboBox.blockSignals(True)
        for label in self.tabWidget.labelSet():
            if self.comboBox.findText(label) == -1:
                self.addedLabels.append(label)
                self.comboBox.addItem(label, Qt.DisplayRole)

        self.setText(f"Open {self.filenames}")


class SendToCommand(QUndoCommand):

    """ Send a row to another tab.
    This action will:
    * remove a row from origin tab at origin row, which will update all
      row indices of remaining rows in the tab,
    * append this row to the target tab
    * remove corresponding box from graphicsScene, which will update all
      row indices of other boxes from the same tab
    * change box color, tab index, row index and tab name
      (which affect the tooltip)
    * add back the box to the graphicsScene
    Undoing will do exactly the same actions as redo but:
    * the row and box are inserted back to their original row, which in
      turn update the row indices of all boxes from the same tab.
    * restore graphicsScene item and page only if the page was different,
    """

    def __init__(self, originIndex, targetIndex, originRow, tabWidget,
                 graphicsScene, parent=None):
        super().__init__(parent)
        self.originIndex = originIndex
        self.targetIndex = targetIndex
        self.originRow = originRow
        self.tabWidget: TabWidget = tabWidget
        self.graphicsScene: GraphicsScene = graphicsScene
        self.targetRow = None
        self.page = self.graphicsScene.page
        self.items = self.graphicsScene.items()

    def undo(self):
        originModel = self.tabWidget.getTableModel(self.originIndex)
        targetModel = self.tabWidget.getTableModel(self.targetIndex)
        rowData = targetModel.rowAtIndex(self.targetRow)
        targetModel.deleteRow(self.targetRow)
        originModel.insertRow(self.originRow, rowData)

        self.graphicsScene.page = self.page
        self.graphicsScene.removeAllItems()
        for item in self.items:
            self.graphicsScene.addItem(item)

    def redo(self):
        originModel = self.tabWidget.getTableModel(self.originIndex)
        targetModel = self.tabWidget.getTableModel(self.targetIndex)
        rowData = originModel.rowAtIndex(self.originRow)
        originModel.deleteRow(self.originRow)
        targetModel.appendRow(rowData)
        self.targetRow = targetModel.rowCount(QModelIndex()) - 1

        rect = self.graphicsScene.removeBox(self.originIndex, self.originRow)
        self.graphicsScene.addBox(
            self.targetIndex, self.tabWidget.tabText(self.targetIndex),
            self.targetRow, rect.page, rect.label, rect.rect(),
            self.tabWidget.color_map(self.targetIndex)[rect.label])

        self.setText(f"Sending {self.originRow} from {originModel} to {targetModel}")


class CellClickedCommand(QUndoCommand):

    """ Move the view to the new selected cell.
    This action will:
    * if the box is in a new page, remove all items and add all items of the
      new page.
    * select the new cell
    * move the view to the newly selected box,
    Undoing this action will:
    * if a new page was shown when doing this action, restore all previous
      items and page,
    * restore previous viewport
    * restore previous selected item.
    """

    def __init__(self, tabIndex, cellIndex, prevTabIndex, prevCellIndex,
                 tabWidget, graphicsScene, graphicsView, comboBox,
                 parent=None):
        super().__init__(parent)
        self.tabIndex = tabIndex
        self.row = cellIndex.row()
        self.col = cellIndex.column()
        self.prevTabIndex = prevTabIndex
        self.prevRow = prevCellIndex.row()
        self.prevCol = prevCellIndex.column()
        self.tabWidget: TabWidget = tabWidget
        self.graphicsScene: GraphicsScene = graphicsScene
        self.graphicsView: SmoothView = graphicsView
        self.comboBox: QComboBox = comboBox
        self.previousSceneRect = self.graphicsView.mapToScene(
            graphicsView.viewport().geometry()).boundingRect()
        self.items = self.graphicsScene.items()
        self.page = self.graphicsScene.page
        self.label = self.comboBox.currentText()

    def undo(self):
        if self.page != self.graphicsScene.page or \
                self.tabIndex != self.prevTabIndex:
            self.graphicsScene.page = self.page
            self.graphicsScene.removeAllItems()
            for item in self.items:
                self.graphicsScene.addItem(item)
        if self.prevTabIndex >= 0:
            self.tabWidget.setCurrentIndex(self.prevTabIndex)
            self.tabWidget.previousCellIndex = self.prevTabIndex
        else:
            self.prevTabIndex = self.tabWidget.currentIndex()
        self.tabWidget.getTableView(self.prevTabIndex).clearSelection()
        prevCellIndex = self.tabWidget.getCurrentTableModel().index(
            self.prevRow, self.prevCol)
        self.tabWidget.setCurrentSelectedCell(prevCellIndex)
        self.graphicsView.fitInView(self.previousSceneRect)
        self.graphicsView.setFocus()
        self.tabWidget.previousCellIndex = prevCellIndex
        self.tabWidget.previousTabIndex = self.prevTabIndex
        self.comboBox.blockSignals(True)
        self.comboBox.setCurrentText(self.label)
        self.comboBox.blockSignals(False)

    def redo(self):
        self.tabWidget.setCurrentIndex(self.tabIndex)
        self.tabWidget.getTableView(self.tabIndex).clearSelection()
        model = self.tabWidget.getCurrentTableModel()
        cellIndex = model.index(self.row, self.col)
        self.tabWidget.setCurrentSelectedCell(cellIndex)
        page = model.pageAtIndex(cellIndex)
        if page != self.page:
            filename = self.tabWidget.widget(self.tabIndex).filename
            pattern = os.path.join(os.path.dirname(filename), page + ".*")
            imageName = glob.glob(pattern)
            if not imageName:
                self.messageLabel.setText(f"{page} image not found")
                return
            self.graphicsScene.removeAllItems()
            pixmap = QPixmap(imageName[0])
            self.graphicsScene.setPage(page, pixmap)
        if page != self.page or self.tabIndex != self.prevTabIndex:
            self.graphicsScene.removeAllBoxes()
            for tabIndex, pageData in enumerate(
                    self.tabWidget.pageDatas(page)):
                tabName = self.tabWidget.tabText(tabIndex)
                for rowIndex, rowData in pageData.iterrows():
                    label = rowData["label"]
                    color = self.tabWidget.color_map(tabIndex)[label]
                    self.graphicsScene.addBox(
                        tabIndex, tabName, rowIndex, page, label,
                        rowData["box"], color)
        box = self.graphicsScene.box(self.tabIndex, self.row)
        boundingRect = box.boundingRect()
        margin_size = min(boundingRect.width(), boundingRect.height()) * 2
        margin = QMarginsF(*([margin_size] * 4))
        viewRect = boundingRect + margin
        self.graphicsView.fitInView(viewRect, Qt.KeepAspectRatio)
        self.graphicsView.setFocus()
        self.comboBox.blockSignals(True)
        self.comboBox.setCurrentText(box.label)
        self.comboBox.blockSignals(False)
        self.setText(f"clicked row {self.tabIndex}:{self.row}")

    def id(self):
        return 4

    def mergeWith(self, other):
        if self.id() != other.id():
            return False

        if self.tabIndex == other.tabIndex:
            self.row = other.row
            self.col = other.col
            self.setText(f"clicked row {self.tabIndex}:{self.row}")
            return True

        return False


class LabelChangedCommand(QUndoCommand):

    """ Label of the current element changed using the comboBox
    This action will:
    * set the label of the corresponding row in tablemodel
    * set the correct color of the corresponding box
    Undoing will:
    * set the previous label in the comboBox
    * set the previous label in the tablemodel
    * set the previous color of the corresponding box
    """

    def __init__(self, label, tabIndex, cellIndex, tabWidget, graphicsScene,
                 comboBox, parent=None):
        super().__init__(parent)

        self.label = label
        self.tabIndex = tabIndex
        self.cellIndex = cellIndex
        self.tabWidget: TabWidget = tabWidget
        self.graphicsScene: GraphicsScene = graphicsScene
        self.comboBox: QComboBox = comboBox
        self.prevLabel = self.tabWidget.getTableModel(tabIndex).labelAtIndex(
            cellIndex)
        self.prevColor = self.graphicsScene.box(
            tabIndex, cellIndex.row()).color

    def undo(self):
        self.tabWidget.getTableModel(self.tabIndex).setLabel(
            self.cellIndex.row(), self.prevLabel)
        self.comboBox.blockSignals(True)
        self.comboBox.setCurrentText(self.prevLabel)
        self.comboBox.blockSignals(False)
        self.graphicsScene.box(self.tabIndex, self.cellIndex.row()).setColor(
            self.prevColor)
        self.tabWidget.setCurrentIndex(self.tabIndex)

    def redo(self):
        self.comboBox.blockSignals(True)
        self.comboBox.setCurrentText(self.label)
        self.comboBox.blockSignals(False)
        self.tabWidget.getTableModel(self.tabIndex).setLabel(
            self.cellIndex.row(), self.label)
        color_map = self.tabWidget.color_map(self.tabIndex)
        self.graphicsScene.box(self.tabIndex, self.cellIndex.row()).setColor(
            color_map[self.label])
        self.setText(f"Change box label to {self.label}")

    def id(self):
        return 3

    def mergeWith(self, other):
        if self.id() != other.id():
            return False

        if self.cellIndex.row() == other.cellIndex.row() and \
                self.tabIndex == other.tabIndex:
            self.label = other.label
            self.setText(f"Change box label to {self.label}")
            return True

        return False


class SelectBoxCommand(QUndoCommand):

    """ Select a box using the mouse on graphicsview.
    This will change the selected tab, row and combobox text.
    Will also reset the colors of all boxes.
    """

    def __init__(self, tabIndex, rowIndex, tabWidget, graphicsScene,
                 comboBox, parent=None):
        super().__init__(parent)

        self.tabIndex = tabIndex
        self.rowIndex = rowIndex
        self.tabWidget: TabWidget = tabWidget
        self.graphicsScene: GraphicsScene = graphicsScene
        self.comboBox: QComboBox = comboBox
        self.previousSelectedTabIndex = self.tabWidget.currentIndex()
        self.previousSelectedCell = self.tabWidget.getCurrentSelectedCell()
        self.label = self.comboBox.currentText()

    def undo(self):
        self.tabWidget.setCurrentIndex(self.previousSelectedTabIndex)
        self.tabWidget.getCurrentTableView().clearSelection()
        self.tabWidget.setCurrentSelectedCell(self.previousSelectedCell)
        if self.tabIndex != self.previousSelectedTabIndex:
            for tabIndex in range(self.tabWidget.count()):
                self.graphicsScene.changeTabColor(
                    tabIndex, self.tabWidget.color_map(tabIndex))
        self.comboBox.blockSignals(True)
        self.comboBox.setCurrentText(self.label)
        self.comboBox.blockSignals(False)

    def redo(self):
        self.tabWidget.setCurrentIndex(self.tabIndex)
        self.tabWidget.getCurrentTableView().clearSelection()
        model = self.tabWidget.getCurrentTableModel()
        modelIndex = model.index(self.rowIndex, 2)
        self.tabWidget.setCurrentSelectedCell(modelIndex)
        if self.tabIndex != self.previousSelectedTabIndex:
            for tabIndex in range(self.tabWidget.count()):
                self.graphicsScene.changeTabColor(
                    tabIndex, self.tabWidget.color_map(tabIndex))
        self.comboBox.blockSignals(True)
        self.comboBox.setCurrentText(model.labelAtIndex(modelIndex))
        self.comboBox.blockSignals(False)
        self.setText(f"select box {self.tabIndex}:{self.rowIndex}")

    def id(self):
        return 2

    def mergeWith(self, other):
        if self.id() != other.id():
            return False

        if self.tabIndex == other.tabIndex:
            self.rowIndex = other.rowIndex
            return True

        return False


class MoveBoxCommand(QUndoCommand):

    """Move a box.
    This will modify only the tablemodel with the new box.
    """

    def __init__(self, tabIndex, rowIndex, box, tabWidget, graphicsScene,
                 parent=None):
        super().__init__(parent)

        self.tabIndex = tabIndex
        self.rowIndex = rowIndex
        self.box = box
        self.tabWidget: TabWidget = tabWidget
        self.graphicsScene: GraphicsScene = graphicsScene
        model = self.tabWidget.getTableModel(self.tabIndex)
        modelIndex = model.index(self.rowIndex, 2)
        self.previousBox = self.tabWidget.getCurrentTableModel().boxAtIndex(
            modelIndex)

    def undo(self):
        model: TableModel = self.tabWidget.getTableModel(self.tabIndex)
        modelIndex = model.index(self.rowIndex, 2)
        model.setData(modelIndex, self.previousBox, Qt.EditRole)
        self.graphicsScene.box(self.tabIndex, self.rowIndex).setRect(
            self.previousBox)

    def redo(self):
        model: TableModel = self.tabWidget.getTableModel(self.tabIndex)
        modelIndex = model.index(self.rowIndex, 2)
        model.setData(modelIndex, self.box, Qt.EditRole)
        self.graphicsScene.box(self.tabIndex, self.rowIndex).setRect(
            self.box)
        self.setText(f"Moving box to {self.box}")

    def id(self):
        return 1

    def mergeWith(self, other):
        if other.id() != self.id():
            return False

        self.box = other.box
        self.setText(f"Moving box to {self.box}")
        return True


class ViewportMovedCommand(QUndoCommand):

    """Viewport of graphicsview has moved."""

    def __init__(self, rect, prevRect, graphicsView, parent=None):
        super().__init__(parent)

        self.rect = rect
        self.prevRect = prevRect
        self.graphicsView: SmoothView = graphicsView

    def undo(self):
        self.graphicsView.fitInView(self.prevRect)

    def redo(self):
        self.graphicsView.fitInView(self.rect)
        self.setText(f"Moved view to {self.rect}")

    def id(self):
        return 5

    def mergeWith(self, other):
        if other.id() != self.id():
            return False
        
        if isinstance(other, ViewportMovedCommand):
            self.rect = other.rect
            self.setText(f"Moved view to {self.rect}")
            return True
        return False


class DeleteItemCommand(QUndoCommand):

    """Delete selected item"""

    def __init__(self, tabIndex, cellIndex, tabWidget, graphicsView,
                 graphicsScene, comboBox, parent=None):
        super().__init__(parent)

        self.tabIndex = tabIndex
        self.cellIndex = cellIndex
        self.tabWidget: TabWidget = tabWidget
        self.graphicsView: SmoothView = graphicsView
        self.graphicsScene: GraphicsScene = graphicsScene
        self.comboBox: QComboBox = comboBox
        self.rowData = self.cellIndex.model().rowAtIndex(self.cellIndex.row())
        self.rect = self.graphicsScene.box(tabIndex, cellIndex.row())
        self.previousSceneRect = self.graphicsView.mapToScene(
            graphicsView.viewport().geometry()).boundingRect()
        
    def undo(self):
        model = self.tabWidget.getTableModel(self.tabIndex)
        model.insertRow(self.cellIndex.row(), self.rowData)
        self.graphicsScene.insertBox(self.tabIndex, self.cellIndex.row(),
                                     self.rect)
        self.graphicsView.fitInView(self.previousSceneRect)
        self.comboBox.setCurrentText(self.rect.label)

    def redo(self):
        model = self.tabWidget.getTableModel(self.tabIndex)
        model.deleteRow(self.cellIndex.row())
        self.graphicsScene.removeBox(self.tabIndex, self.cellIndex.row())


class CreateItemCommand(QUndoCommand):

    """Create new rect"""

    def __init__(self, rect, tabWidget, graphicsScene, comboBox, parent=None):
        super().__init__(parent)

        self.rect: ResizableRect = rect
        self.tabWidget: TabWidget = tabWidget
        self.graphicsScene: GraphicsScene = graphicsScene
        self.comboBox: QComboBox = comboBox
        self.label = comboBox.currentText()

    def undo(self):
        model: TableModel = self.tabWidget.getTableModel(self.rect.tabIndex)
        model.deleteRow(self.rect.rowIndex)
        self.graphicsScene.removeBox(self.rect.tabIndex, self.rect.rowIndex)
        self.comboBox.setCurrentText(self.label)

    def redo(self):
        model: TableModel = self.tabWidget.getTableModel(self.rect.tabIndex)
        rowData = model.makeRowData(self.rect.page, self.rect.label,
                                    self.rect.rect())
        model.appendRow(rowData)
        if self.graphicsScene.box(
                self.rect.tabIndex, self.rect.rowIndex) is None:
            self.graphicsScene.insertBox(
                self.rect.tabIndex, self.rect.rowIndex, self.rect)
        self.comboBox.setCurrentText(self.rect.label)
