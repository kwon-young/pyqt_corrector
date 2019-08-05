from PySide2.QtWidgets import QMainWindow
from PySide2.QtCore import QFile
from PySide2.QtUiTools import QUiLoader

from pyqt_corrector.mainwindow_ui import Ui_MainWindow


class MainWindow(QMainWindow):

    """Docstring for MainWindow. """

    def __init__(self):
        """Constructor """
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.show()
