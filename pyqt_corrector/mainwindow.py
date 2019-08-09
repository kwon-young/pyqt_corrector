"""
File: mainwindow.py
Author: Kwon-Young Choi
Email: kwon-young.choi@hotmail.fr
Date: 2019-08-05
Description: MainWindow
"""
import os
import glob
import pandas as pd

from PySide2.QtWidgets import QMainWindow, QFileDialog, QApplication, QWidget, QGridLayout, QTableView, QLabel
from PySide2.QtCore import QFile, Signal, Slot, QModelIndex, Qt, QTime, QTimer
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QIcon

from pyqt_corrector.mainwindow_ui import Ui_MainWindow
from pyqt_corrector.models import TableModel
from pyqt_corrector.widgets import ImageViewer, LabelComboBox, ResizableRect


class MainWindow(QMainWindow):

    """Docstring for MainWindow. """

    changedDirectory = Signal()
    datasetsChanged = Signal()

    def __init__(self):
        """Constructor """
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.openIcon = QIcon().fromTheme("document-open")
        self.ui.actionOpen_Directory.setIcon(self.openIcon)
        self.ui.actionOpen_Directory.triggered.connect(self.openDirectory)
        self.saveIcon = QIcon().fromTheme("document-save")
        self.ui.actionSave_Dataset.setIcon(self.saveIcon)
        self.ui.actionSave_Dataset.triggered.connect(self.saveDataToDisk)

        self.messageLabel = QLabel()
        self.ui.statusbar.addWidget(self.messageLabel)
        self.coordLabel = QLabel()
        self.ui.statusbar.addWidget(self.coordLabel)
        self.stopwatchLabel = QLabel()
        self.ui.statusbar.addWidget(self.stopwatchLabel)

        self.time = QTime(0, 0)
        self.stopwatch = QTimer()
        self.stopwatch.setInterval(1000)
        self.stopwatch.timeout.connect(self.updateStopWatchLabel)

        self.stopwatchStartIcon = QIcon().fromTheme("chronometer-start")
        self.ui.actionStopwatch_Start.setIcon(self.stopwatchStartIcon)
        self.ui.actionStopwatch_Start.triggered.connect(self.startStopWatch)

        self.stopwatchStopIcon = QIcon().fromTheme("chronometer-pause")
        self.ui.actionStopwatch_Stop.setIcon(self.stopwatchStopIcon)
        self.ui.actionStopwatch_Stop.triggered.connect(self.stopStopWatch)

        self.stopwatchResetIcon = QIcon().fromTheme("chronometer-reset")
        self.ui.actionStopwatch_Reset.setIcon(self.stopwatchResetIcon)
        self.ui.actionStopwatch_Reset.triggered.connect(self.resetStopWatch)

        self.comboBox = LabelComboBox(self.ui.scrollAreaWidgetContents)
        self.comboBox.setEditable(True)
        self.comboBox.setObjectName("comboBox")
        self.ui.actionNext_label.triggered.connect(self.selectNextLabel)
        self.ui.actionPrevious_label.triggered.connect(self.selectPreviousLabel)
        self.ui.gridLayout_2.addWidget(self.comboBox, 0, 0, 1, 1)

        self.imageViewer = ImageViewer(
            self.comboBox, self.ui.scrollAreaWidgetContents)
        self.ui.gridLayout_2.addWidget(self.imageViewer.view, 1, 0, 1, 1)
        self.imageViewer.message.connect(self.messageLabel.setText)
        self.imageViewer.view.mouseMoved.connect(self.coordLabel.setText)
        self.imageViewer.signalHandler.boxPressed.connect(
            self.messageLabel.setText)
        self.imageViewer.signalHandler.boxPressed.connect(self.selectRowColumn)
        self.imageViewer.signalHandler.boxChanged.connect(self.changeBox)
        self.imageViewer.LabelComboBoxChanged.connect(
            self.setSelectedItemLabel)

        self.leftIcon = QIcon().fromTheme("go-previous")
        self.ui.leftPushButton.setIcon(self.leftIcon)
        self.ui.leftPushButton.clicked.connect(self.moveRowToPrevious)
        self.ui.actionSend_to_left_tab.triggered.connect(self.moveRowToPrevious)
        self.rightIcon = QIcon().fromTheme("go-next")
        self.ui.rightPushButton.setIcon(self.rightIcon)
        self.ui.rightPushButton.clicked.connect(self.moveRowToNext)
        self.ui.actionSend_to_right_tab.triggered.connect(self.moveRowToNext)
        self.tabs = []
        self.gridLayouts_1 = []
        self.gridLayouts_2 = []
        self.tableViews = []
        self.tableModels = []
        self.tableNames = []

        self.ui.actionNext_box.triggered.connect(self.selectNextRow)
        self.ui.actionPrevious_box.triggered.connect(self.selectPreviousRow)

        self.changedDirectory.connect(self.readData)

        self.dataset_files = []
        self.datasets = {}
        self.datasetsChanged.connect(self.updateTabWidget)

        self.show()

    @Slot()
    def openDirectory(self):
        """Open dataset directory"""
        self.setWindowFilePath(QFileDialog.getExistingDirectory(
            self,
            QApplication.translate("MainWindow", "Open directory", None, -1),
            "/home/kwon-young/Documents/PartageVirtualBox/data/omr_dataset/choi_dataset"))
        self.setWindowTitle(f"Corrector {self.windowFilePath()} [*]")
        self.imageViewer.directory = self.windowFilePath()
        self.changedDirectory.emit()

    @Slot()
    def readData(self):
        """Read csv data into pandas DataFrame"""
        self.dataset_files = glob.glob(os.path.join(self.windowFilePath(), "*.csv"))
        labels = set()
        if not self.dataset_files:
            self.messageLabel.setText(
                f"No .csv files found in {self.windowFilePath()}")
        for name in self.dataset_files:
            dataset = pd.read_csv(
                name, header=0, skipinitialspace=True, skip_blank_lines=True,
                comment="#")
            for col in ["page", "label", "box"]:
                if col not in dataset:
                    self.messageLabel.setText(
                        f"{name} does not have column {col}")
                    break
            else:
                self.datasets[name] = dataset
            labels |= set(dataset["label"].unique())
        existingLabels = [self.comboBox.itemText(i)
                          for i in range(self.comboBox.count())]
        for label in labels:
            if label not in existingLabels:
                self.comboBox.addItem(label)

        self.datasetsChanged.emit()

    @Slot()
    def updateTabWidget(self):
        numTabs = self.ui.tabWidget.count()
        for i, (name, dataset) in enumerate(self.datasets.items()):
            if i < numTabs:
                self.updateTab(i, name, dataset)
            else:
                self.createTab(name, dataset)
            self.tableViews[i].activated.connect(
                self.imageViewer.updateSelect)
        for i in range(len(self.datasets), numTabs):
            self.deleteTab(i)
        self.imageViewer.dataModels = self.tableModels
        self.imageViewer.dataNames = self.tableNames

    def createTab(self, name, dataset):
        """Create a tab for dataset"""
        name = os.path.basename(name)
        tab_index = len(self.tabs)

        tab = QWidget()
        tab.setObjectName(f"tab_{tab_index}")
        self.tabs.append(tab)

        gridLayout_2 = QGridLayout(tab)
        gridLayout_2.setObjectName(f"gridLayout_2_{tab_index}")
        self.gridLayouts_2.append(gridLayout_2)

        gridLayout_1 = QGridLayout()
        gridLayout_1.setObjectName(f"gridLayout_1_{tab_index}")
        self.gridLayouts_1.append(gridLayout_1)

        tableView = QTableView(tab)
        tableView.setObjectName(f"tableView_{tab_index}")
        self.tableViews.append(tableView)

        tableModel = TableModel(self)
        tableModel.update(dataset)
        self.tableModels.append(tableModel)

        self.tableNames.append(name)

        tableView.setModel(tableModel)
        gridLayout_1.addWidget(tableView, 0, 0, 1, 1)
        gridLayout_2.addLayout(gridLayout_1, 0, 0, 1, 1)
        self.ui.tabWidget.addTab(tab, "")

        self.ui.tabWidget.setTabText(
            self.ui.tabWidget.indexOf(tab),
            QApplication.translate("MainWindow", name, None, -1))
        tableView.resizeColumnsToContents()

    def updateTab(self, tab_index, name, dataset):
        """Update existing Tab"""
        name = os.path.basename(name)
        tableModel = TableModel(self)
        tableModel.update(dataset)
        self.tableModels[tab_index] = tableModel

        self.tableViews[tab_index].setModel(tableModel)
        self.tableNames[tab_index] = name

        self.ui.tabWidget.setTabText(
            tab_index, QApplication.translate("MainWindow", name, None, -1))
        return

    def deleteTab(self, tab_index):
        self.tableViews[tab_index].activated.disconnect(
            self.imageViewer.update)
        self.ui.tabWidget.removeTab(tab_index)
        del self.tableNames[tab_index]
        del self.tableModels[tab_index]
        del self.tableViews[tab_index]
        del self.gridLayouts_1[tab_index]
        del self.gridLayouts_2[tab_index]
        del self.tabs[tab_index]

    @Slot()
    def selectRowColumn(self, name, row):
        index = self.tableNames.index(name)
        self.ui.tabWidget.setCurrentIndex(index)
        modelIndex = self.tableModels[index].index(row, 2)
        self.tableViews[index].setCurrentIndex(modelIndex)
        label = self.tableModels[index].labelAtIndex(modelIndex)
        self.comboBox.setCurrentText(label)
        self.comboBox.row = row

    @Slot()
    def selectNextRow(self):
        if self.ui.tabWidget.count() > 0:
            tabIndex = self.ui.tabWidget.currentIndex()
            view: QTableView = self.tableViews[tabIndex]
            index = view.currentIndex()
            model: TableModel = self.tableModels[tabIndex]
            rowCount = model.rowCount(QModelIndex())
            nextIndex: QModelIndex = model.index((index.row() + 1) % rowCount,
                                                 index.column())
            if nextIndex.isValid():
                view.setCurrentIndex(nextIndex)
                view.activated.emit(nextIndex)

    @Slot()
    def selectPreviousRow(self):
        if self.ui.tabWidget.count() > 0:
            tabIndex = self.ui.tabWidget.currentIndex()
            view: QTableView = self.tableViews[tabIndex]
            index = view.currentIndex()
            model: TableModel = self.tableModels[tabIndex]
            rowCount = model.rowCount(QModelIndex())
            previousIndex: QModelIndex = model.index(
                (rowCount + index.row() - 1) % rowCount, index.column())
            if previousIndex.isValid():
                view.setCurrentIndex(previousIndex)
                view.activated.emit(previousIndex)

    @Slot()
    def selectNextLabel(self):
        if self.comboBox.count() > 0:
            index = self.comboBox.currentIndex()
            newIndex = (index + 1) % self.comboBox.count()
            self.comboBox.setCurrentIndex(newIndex)
            self.comboBox.activated.emit(newIndex)

    @Slot()
    def selectPreviousLabel(self):
        if self.comboBox.count() > 0:
            index = self.comboBox.currentIndex()
            newIndex = (self.comboBox.count() + index - 1) % self.comboBox.count()
            self.comboBox.setCurrentIndex(newIndex)
            self.comboBox.activated.emit(newIndex)

    @Slot()
    def changeBox(self, name, row, box):
        index = self.tableNames.index(name)
        model = self.tableModels[index]
        indexModel = model.index(row, 2)
        model.setData(indexModel, box, Qt.EditRole)
        self.setWindowModified(True)

    @Slot()
    def setSelectedItemLabel(self, row, label):
        tabIndex = self.ui.tabWidget.currentIndex()
        if tabIndex >= 0:
            model: TableModel = self.tableModels[tabIndex]
            index = model.index(row, 1)
            model.setData(index, label, Qt.EditRole)
            self.setWindowModified(True)
            rect: ResizableRect = self.imageViewer.curRect
            if rect is not None and self.imageViewer.color_map is not None:
                rect.setColor(self.imageViewer.color_map[label])
                name = self.tableNames[tabIndex]
                rect.setToolTip(f"{name}: {label}")
                rect.setData(0, name)
                rect.setData(1, row)

    @Slot()
    def moveRowToNext(self, checked):
        numTab = self.ui.tabWidget.count()
        if numTab > 0:
            tabIndex = self.ui.tabWidget.currentIndex()
            model: TableModel = self.tableModels[tabIndex]
            nextModel: TableModel = self.tableModels[(tabIndex + 1) % numTab]
            view: QTableView = self.tableViews[tabIndex]
            modelIndex: QModelIndex = view.currentIndex()
            currentRow = modelIndex.row()
            rowData = model.rowAtIndex(currentRow)
            model.deleteRow(currentRow)
            nextModel.appendRow(rowData)
            self.setWindowModified(True)

    @Slot()
    def moveRowToPrevious(self, checked):
        numTab = self.ui.tabWidget.count()
        if numTab > 0:
            tabIndex = self.ui.tabWidget.currentIndex()
            model: TableModel = self.tableModels[tabIndex]
            nextModel: TableModel = self.tableModels[(tabIndex - 1) % numTab]
            view: QTableView = self.tableViews[tabIndex]
            modelIndex: QModelIndex = view.currentIndex()
            currentRow = modelIndex.row()
            rowData = model.rowAtIndex(currentRow)
            model.deleteRow(currentRow)
            nextModel.appendRow(rowData)
            self.setWindowModified(True)

    @Slot()
    def saveDataToDisk(self):
        self.setWindowModified(False)
        for name, model in zip(self.dataset_files, self.tableModels):
            model._data.to_csv(name + ".bak", index=False)
        return

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
