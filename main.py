"""
File: main2.py
Author: Kwon-Young Choi
Email: kwon-young.choi@irisa.fr
Date: 2019-08-12
Description: main
"""

import sys
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication
from PySide2 import QtCore
from PySide2.QtCore import QFile, QCoreApplication

from pyqt_corrector.mainwindow import MainWindow
from pyqt_corrector.smoothview import SmoothView
from pyqt_corrector.tabwidget import TabWidget


if __name__ == "__main__":
    QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    app = QApplication([])
    file = QFile("data/mainwindow.ui")
    file.open(QFile.ReadOnly)
    loader = QUiLoader()
    loader.registerCustomWidget(MainWindow)
    loader.registerCustomWidget(SmoothView)
    loader.registerCustomWidget(TabWidget)
    main_window = loader.load(file)
    main_window.setupUi()
    main_window.show()
    sys.exit(app.exec_())
