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
from PySide2.QtCore import QFile, Signal, Slot, QModelIndex, Qt
from PySide2.QtUiTools import QUiLoader

from pyqt_corrector.mainwindow_ui import Ui_MainWindow
from pyqt_corrector.models import TableModel
from pyqt_corrector.widgets import ImageViewer, LabelComboBox


class MainWindow(QMainWindow):

    """Docstring for MainWindow. """

    changedDirectory = Signal()
    datasetsChanged = Signal()

    def __init__(self):
        """Constructor """
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.actionOpen_directory.triggered.connect(self.openDirectory)

        self.messageLabel = QLabel()
        self.ui.statusbar.addWidget(self.messageLabel)
        self.coordLabel = QLabel()
        self.ui.statusbar.addWidget(self.coordLabel)

        self.comboBox = LabelComboBox(self.ui.scrollAreaWidgetContents)
        self.comboBox.setEditable(True)
        self.comboBox.setObjectName("comboBox")
        self.ui.gridLayout.addWidget(self.comboBox, 0, 0, 1, 1)

        self.imageViewer = ImageViewer(
            self.comboBox, self.ui.scrollAreaWidgetContents)
        self.ui.gridLayout.addWidget(self.imageViewer.view, 1, 0, 1, 1)
        self.imageViewer.message.connect(self.messageLabel.setText)
        self.imageViewer.view.mouseMoved.connect(self.coordLabel.setText)
        self.imageViewer.signalHandler.boxPressed.connect(
            self.messageLabel.setText)
        self.imageViewer.signalHandler.boxPressed.connect(self.selectRowColumn)
        self.imageViewer.signalHandler.boxChanged.connect(self.changeBox)
        self.imageViewer.LabelComboBoxChanged.connect(
            self.setSelectedItemLabel)

        self.tabs = []
        self.gridLayouts_1 = []
        self.gridLayouts_2 = []
        self.tableViews = []
        self.tableModels = []
        self.tableNames = []

        self.directory = None
        self.changedDirectory.connect(self.readData)

        self.datasets = {}
        self.datasetsChanged.connect(self.updateTabWidget)

        self.show()

    @Slot()
    def openDirectory(self):
        """Open dataset directory"""
        self.directory = QFileDialog.getExistingDirectory(
            self,
            QApplication.translate("MainWindow", "Open directory", None, -1),
            "/home/kwon-young/Documents/choi_dataset")
        self.imageViewer.directory = self.directory
        self.changedDirectory.emit()

    @Slot()
    def readData(self):
        """Read csv data into pandas DataFrame"""
        dataset_files = glob.glob(os.path.join(self.directory, "*.csv"))
        labels = set()
        if not dataset_files:
            self.messageLabel.setText(
                f"No .csv files found in {self.directory}")
        for name in dataset_files:
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
        self.tableViews[index].selectRow(row)

    @Slot()
    def changeBox(self, name, row, box):
        index = self.tableNames.index(name)
        model = self.tableModels[index]
        indexModel = model.index(row, 2)
        model.setData(indexModel, box, Qt.EditRole)

    @Slot()
    def setSelectedItemLabel(self, row, label):
        index = self.ui.tabWidget.currentIndex()
        print(index)
        if index >= 0:
            model: TableModel = self.tableModels[index]
            index = model.index(row, 1)
            model.setData(index, label, Qt.EditRole)
