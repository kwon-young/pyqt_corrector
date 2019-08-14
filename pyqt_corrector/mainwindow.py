"""
File: mainwindow2.py
Author: Kwon-Young Choi
Email: kwon-young.choi@irisa.fr
Date: 2019-08-12
Description: MainWindow
"""
from PySide2.QtWidgets import QApplication, QMainWindow, QFileDialog, \
    QLabel, QUndoStack, QUndoView
from PySide2.QtCore import Slot, Qt, QModelIndex, QRectF, QTime, QTimer
from PySide2.QtGui import QKeySequence, QIcon
from pyqt_corrector.commands import OpenDatasetCommand, DeleteDatasetCommand, \
    SendToCommand, CellClickedCommand, LabelChangedCommand, SelectBoxCommand, \
    MoveBoxCommand, ViewportMovedCommand, DeleteItemCommand, CreateItemCommand
from pyqt_corrector.graphicsscene import GraphicsScene
from pyqt_corrector.graphicsitem import ResizableRect


class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.undoStack = QUndoStack(self)
        self.undoStack.cleanChanged.connect(self.cleanChanged)

        self.undoAction = self.undoStack.createUndoAction(self, "&Undo")
        self.undoAction.setShortcut(QKeySequence.Undo)

        self.redoAction = self.undoStack.createRedoAction(self, "&Redo")
        self.redoAction.setShortcut(QKeySequence.Redo)

        self.messageLabel = QLabel()
        self.coordLabel = QLabel()
        self.stopwatchLabel = QLabel()

        self.time = QTime(0, 0)
        self.stopwatch = QTimer()

        self.undoView = QUndoView(self.undoStack)

        self.graphicsScene = GraphicsScene(self)

    def setupUi(self):
        self.openIcon = QIcon().fromTheme("document-open")
        self.actionOpen_Datasets.setIcon(self.openIcon)
        self.saveIcon = QIcon().fromTheme("document-save")
        self.actionSave.setIcon(self.saveIcon)
        self.closeIcon = QIcon().fromTheme("document-close")
        self.actionClose_Dataset.setIcon(self.closeIcon)

        self.statusbar.addWidget(self.messageLabel)
        self.statusbar.addWidget(self.coordLabel)
        self.statusbar.addWidget(self.stopwatchLabel)

        self.stopwatch.setInterval(1000)
        self.stopwatch.timeout.connect(self.updateStopWatchLabel)

        self.stopwatchStartIcon = QIcon().fromTheme("chronometer-start")
        self.actionTimer_Start.setIcon(self.stopwatchStartIcon)
        self.actionTimer_Start.triggered.connect(self.startStopWatch)

        self.stopwatchStopIcon = QIcon().fromTheme("chronometer-pause")
        self.actionTimer_Stop.setIcon(self.stopwatchStopIcon)
        self.actionTimer_Stop.triggered.connect(self.stopStopWatch)

        self.stopwatchResetIcon = QIcon().fromTheme("chronometer-reset")
        self.actionTimer_Reset.setIcon(self.stopwatchResetIcon)
        self.actionTimer_Reset.triggered.connect(self.resetStopWatch)

        self.leftIcon = QIcon().fromTheme("go-previous")
        self.actionSend_To_Left.setIcon(self.leftIcon)
        self.rightIcon = QIcon().fromTheme("go-next")
        self.actionSend_To_Right.setIcon(self.rightIcon)
        self.upIcon = QIcon().fromTheme("go-up")
        self.actionPrevious_Item.setIcon(self.upIcon)
        self.downIcon = QIcon().fromTheme("go-down")
        self.actionNext_Item.setIcon(self.downIcon)

        self.undoView.setWindowTitle("Command List")
        self.undoView.show()
        self.undoView.setAttribute(Qt.WA_QuitOnClose, False)

        self.menuEdit.addAction(self.undoAction)
        self.menuEdit.addAction(self.redoAction)

        self.graphicsView.setScene(self.graphicsScene)
        self.graphicsView.mouseMoved.connect(self.coordLabel.setText)
        self.graphicsScene.tabWidget = self.tabWidget
        self.graphicsScene.comboBox = self.comboBox
        self.graphicsScene.signalHandler.boxPressed.connect(self.selectBox)
        self.graphicsScene.signalHandler.boxChanged.connect(self.changeBox)
        self.graphicsScene.signalHandler.boxCreated.connect(self.createItem)

    @Slot()
    def sendToLeft(self):
        originIndex = self.tabWidget.currentIndex()
        numTabs = self.tabWidget.count()
        targetIndex = (numTabs + originIndex - 1) % numTabs
        modelIndex = self.tabWidget.getCurrentTableView().currentIndex()
        if modelIndex.isValid():
            sendToCommand = SendToCommand(
                originIndex, targetIndex, modelIndex.row(), self.tabWidget,
                self.graphicsView, self.graphicsScene, self.comboBox,
                self.messageLabel)
            self.undoStack.push(sendToCommand)

    @Slot()
    def sendToRight(self):
        originIndex = self.tabWidget.currentIndex()
        numTabs = self.tabWidget.count()
        targetIndex = (originIndex + 1) % numTabs
        modelIndex = self.tabWidget.getCurrentTableView().currentIndex()
        if modelIndex.isValid():
            sendToCommand = SendToCommand(
                originIndex, targetIndex, modelIndex.row(), self.tabWidget,
                self.graphicsView, self.graphicsScene, self.comboBox,
                self.messageLabel)
            self.undoStack.push(sendToCommand)

    @Slot()
    @Slot(int)
    def closeDataset(self, i=-1):
        # put a dialog if there is a pending modification
        # say that modifications are not lost and retrievable with CTRL-Z
        if self.tabWidget.count() > 0:
            if i == -1:
                i = self.tabWidget.currentIndex()
            deleteDatasetCommand = DeleteDatasetCommand(
                [i], self.tabWidget, self.comboBox, self.graphicsView,
                self.graphicsScene)
            self.undoStack.push(deleteDatasetCommand)

    @Slot()
    def openDatasets(self):
        """Open dataset directory"""
        (filenames, _ext) = QFileDialog.getOpenFileNames(
            self,
            QApplication.translate("MainWindow", "Open datasets", None, -1),
            "/home/kwon-young/Documents/PartageVirtualBox/data/omr_dataset/choi_dataset",
            "*.csv")
        if filenames:
            filenames.sort()
            openDatasetCommand = OpenDatasetCommand(
                filenames, self.tabWidget, self.comboBox, self.graphicsView,
                self.graphicsScene, self.messageLabel)
            self.undoStack.push(openDatasetCommand)

    @Slot(int)
    def currentTabChanged(self, index):
        self.tabWidget.setCurrentIndex(index)
        for tabIndex in range(self.tabWidget.count()):
            self.graphicsScene.changeTabColor(
                tabIndex, self.tabWidget.color_map(tabIndex))

    @Slot(int, QModelIndex, int, QModelIndex)
    def cellClicked(self, tabIndex, cellIndex, prevTabIndex, prevCellIndex):
        cellClickedCommand = CellClickedCommand(
            tabIndex, cellIndex, prevTabIndex, prevCellIndex, self.tabWidget,
            self.graphicsScene, self.graphicsView, self.comboBox)
        self.undoStack.push(cellClickedCommand)

    @Slot()
    def SelectNextItem(self):
        if self.tabWidget.count() > 0:
            tabIndex = self.tabWidget.currentIndex()
            prevCellIndex = self.tabWidget.getCurrentSelectedCell()
            model = self.tabWidget.getCurrentTableModel()
            rowCount = model.rowCount(QModelIndex())
            nextRow = (prevCellIndex.row() + 1) % rowCount
            cellIndex = model.index(nextRow, prevCellIndex.column())
            cellClickedCommand = CellClickedCommand(
                tabIndex, cellIndex, tabIndex, prevCellIndex, self.tabWidget,
                self.graphicsScene, self.graphicsView, self.comboBox)
            self.undoStack.push(cellClickedCommand)

    @Slot()
    def SelectPreviousItem(self):
        if self.tabWidget.count() > 0:
            tabIndex = self.tabWidget.currentIndex()
            prevCellIndex = self.tabWidget.getCurrentSelectedCell()
            model = self.tabWidget.getCurrentTableModel()
            rowCount = model.rowCount(QModelIndex())
            nextRow = (rowCount + prevCellIndex.row() - 1) % rowCount
            cellIndex = model.index(nextRow, prevCellIndex.column())
            cellClickedCommand = CellClickedCommand(
                tabIndex, cellIndex, tabIndex, prevCellIndex, self.tabWidget,
                self.graphicsScene, self.graphicsView, self.comboBox)
            self.undoStack.push(cellClickedCommand)

    @Slot()
    def selectNextLabel(self):
        if self.comboBox.count() > 0:
            index = self.comboBox.currentIndex()
            newIndex = (index + 1) % self.comboBox.count()
            label = self.comboBox.itemText(newIndex)
            tabIndex = self.tabWidget.currentIndex()
            cellIndex = self.tabWidget.getCurrentSelectedCell()
            labelChangedCommand = LabelChangedCommand(
                label, tabIndex, cellIndex, self.tabWidget, self.graphicsScene,
                self.comboBox)
            self.undoStack.push(labelChangedCommand)

    @Slot()
    def selectPreviousLabel(self):
        if self.comboBox.count() > 0:
            index = self.comboBox.currentIndex()
            newIndex = ((self.comboBox.count() + index - 1)
                        % self.comboBox.count())
            label = self.comboBox.itemText(newIndex)
            tabIndex = self.tabWidget.currentIndex()
            cellIndex = self.tabWidget.getCurrentSelectedCell()
            labelChangedCommand = LabelChangedCommand(
                label, tabIndex, cellIndex, self.tabWidget, self.graphicsScene,
                self.comboBox)
            self.undoStack.push(labelChangedCommand)

    @Slot(int)
    def labelChanged(self, index):
        label = self.comboBox.itemText(index)
        tabIndex = self.tabWidget.currentIndex()
        cellIndex = self.tabWidget.getCurrentSelectedCell()
        labelChangedCommand = LabelChangedCommand(
            label, tabIndex, cellIndex, self.tabWidget, self.graphicsScene,
            self.comboBox)
        self.undoStack.push(labelChangedCommand)

    @Slot()
    def saveDataToDisk(self):
        self.undoStack.setClean()
        for name, model in zip(self.tabWidget.filenames(),
                               self.tabWidget.models()):
            model.save(name)

    @Slot(bool)
    def cleanChanged(self, clean):
        self.setWindowModified(not clean)

    @Slot(int, int)
    def selectBox(self, tabIndex, rowIndex):
        if tabIndex != self.tabWidget.currentIndex() or \
                rowIndex != self.tabWidget.getCurrentSelectedCell().row():
            selectBoxCommand = SelectBoxCommand(
                tabIndex, rowIndex, self.tabWidget, self.graphicsScene,
                self.comboBox)
            self.undoStack.push(selectBoxCommand)

    @Slot(int, int, QRectF)
    def changeBox(self, tabIndex, rowIndex, box):
        moveBoxCommand = MoveBoxCommand(
            tabIndex, rowIndex, box, self.tabWidget, self.graphicsScene)
        self.undoStack.push(moveBoxCommand)

    @Slot(QRectF, QRectF)
    def viewportMoved(self, rect, prevRect):
        viewportMovedCommand = ViewportMovedCommand(
            rect, prevRect, self.graphicsView)
        self.undoStack.push(viewportMovedCommand)

    @Slot()
    def updateStopWatchLabel(self):
        elapsed = QTime(0, 0).addMSecs(self.time.elapsed())
        self.stopwatchLabel.setText(elapsed.toString())

    @Slot()
    def startStopWatch(self):
        self.time.start()
        self.stopwatch.start(1000)

    @Slot()
    def stopStopWatch(self):
        self.stopwatch.stop()

    @Slot()
    def resetStopWatch(self):
        self.time.start()
        self.stopwatchLabel.setText(QTime(0, 0).toString())

    @Slot()
    def deleteItem(self):
        tabIndex = self.tabWidget.currentIndex()
        cellIndex = self.tabWidget.getCurrentSelectedCell()
        self.undoStack.beginMacro(f"Delete item {tabIndex}:{cellIndex.row()}")
        deleteItemCommand = DeleteItemCommand(
            tabIndex, cellIndex, self.tabWidget, self.graphicsView,
            self.graphicsScene, self.comboBox)
        self.undoStack.push(deleteItemCommand)
        self.cellClicked(tabIndex, cellIndex, tabIndex, cellIndex)
        self.undoStack.endMacro()

    @Slot(ResizableRect)
    def createItem(self, rect):
        self.undoStack.beginMacro(f"Create item {rect.tabIndex}:{rect.rowIndex}")
        createItemCommand = CreateItemCommand(
            rect, self.tabWidget, self.graphicsScene, self.comboBox)
        self.undoStack.push(createItemCommand)
        self.selectBox(rect.tabIndex, rect.rowIndex)
        self.undoStack.endMacro()
