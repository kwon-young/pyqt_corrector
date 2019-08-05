"""
File: main.py
Author: Kwon-Young Choi
Email: kwon-young.choi@hotmail.fr
Date: 2019-08-05
Description: Program entry point
"""

import sys
from pyqt_corrector.mainwindow import MainWindow
from PySide2.QtWidgets import QApplication


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()

    sys.exit(app.exec_())
