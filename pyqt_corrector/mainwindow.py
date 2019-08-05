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

from PySide2.QtWidgets import QMainWindow, QFileDialog, QApplication, QWidget, QGridLayout, QTableView
from PySide2.QtCore import QFile, Signal, Slot
from PySide2.QtUiTools import QUiLoader

from pyqt_corrector.mainwindow_ui import Ui_MainWindow
from pyqt_corrector.models import TableModel


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

        self.tabs = []
        self.gridLayouts_1 = []
        self.gridLayouts_2 = []
        self.tableViews = []
        self.tableModels = []

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
            "")
        self.changedDirectory.emit()

    @Slot()
    def readData(self):
        """Read csv data into pandas DataFrame"""
        dataset_files = glob.glob(os.path.join(self.directory, "*.csv"))
        self.datasets = {name: pd.read_csv(name) for name in dataset_files}
        self.datasetsChanged.emit()

    @Slot()
    def updateTabWidget(self):
        numTabs = self.ui.tabWidget.count()
        for i, (name, dataset) in enumerate(self.datasets.items()):
            if i < numTabs:
                self.updateTab(i, name, dataset)
            else:
                self.createTab(name, dataset)
        for i in range(len(self.datasets), numTabs):
            self.deleteTab(i)

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

        tableView.setModel(tableModel)
        gridLayout_1.addWidget(tableView, 0, 0, 1, 1)
        gridLayout_2.addLayout(gridLayout_1, 0, 0, 1, 1)
        self.ui.tabWidget.addTab(tab, "")

        self.ui.tabWidget.setTabText(
            self.ui.tabWidget.indexOf(tab),
            QApplication.translate("MainWindow", name, None, -1))

    def updateTab(self, tab_index, name, dataset):
        """Update existing Tab"""
        name = os.path.basename(name)
        tableModel = TableModel(self)
        tableModel.update(dataset)
        self.tableModels[tab_index] = tableModel

        self.tableViews[tab_index].setModel(tableModel)

        self.ui.tabWidget.setTabText(
            tab_index, QApplication.translate("MainWindow", name, None, -1))
        return

    def deleteTab(self, tab_index):
        self.ui.tabWidget.removeTab(tab_index)
