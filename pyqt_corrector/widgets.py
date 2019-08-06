import os
import glob
from PySide2.QtWidgets import QWidget, QGraphicsScene, QGraphicsView
from PySide2.QtCore import Slot, Signal, QModelIndex, Qt, QTimeLine, QPointF
from PySide2.QtGui import QPixmap, QWheelEvent, QKeyEvent
from pyqt_corrector.models import TableModel


class SmoothView(QGraphicsView):

    """QGraphicsView with smooth scrolling"""

    def __init__(self, parent=None):
        """Constructor

        """
        super().__init__(parent)

        self._numScheduledScalings = 0
        self._maxScaling = 4
        self._zoomState = False

    @Slot()
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self._zoomState = True

    @Slot()
    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self._zoomState = False

    @Slot()
    def wheelEvent(self, event: QWheelEvent):
        numDegrees = QPointF(event.angleDelta()) / 8.
        #scroll degree wise
        numSteps = numDegrees / 15.  # see QWheelEvent documentation
        if self._zoomState is True:
            if abs(self._numScheduledScalings) < self._maxScaling:
                self._numScheduledScalings += numSteps.y()
            # if user moved the wheel in another direction, we reset previously scheduled scalings
            if self._numScheduledScalings * numSteps.y() < 0:
                self._numScheduledScalings = min(numSteps.y(), self._maxScaling)

            anim: QTimeLine = QTimeLine(350, self)
            anim.setUpdateInterval(20)

            anim.valueChanged.connect(self.scalingTime)
            anim.finished.connect(self.animFinished)
            anim.start()
        else:
            super().wheelEvent(event)

    @Slot()
    def scalingTime(self, x):
        factor = 1.0 + self._numScheduledScalings / 2000.0
        self.scale(factor, factor)

    @Slot()
    def animFinished(self):
        anim = self.sender()
        del anim


class ImageViewer(QWidget):

    """View an image and multiple annotated boxes"""

    imageNotFound = Signal(str)

    def __init__(self, parent):
        """Constructor

        :parent: TODO

        """
        super().__init__(parent)

        self.scene = QGraphicsScene()
        self.scene.clear()

        self.view = SmoothView(self.scene)

        self.directory = None
        self.imageName = None
        self.pixmap = None
        self.rubberBands = []

    @Slot()
    def update(self, index: QModelIndex):
        """Update image and bounding boxes from new index"""
        data: TableModel = index.model()
        row, column = index.row(), index.column()
        page = data.data(data.index(row, 0), Qt.UserRole)
        path = os.path.join(self.directory, f"*{page}*")
        names = glob.glob(path)
        if not names:
            self.imageNotFound.emit(f"no image found in {path}")
            return
        self.imageName = names[0]
        self.pixmap = QPixmap(self.imageName)
        self.scene.addPixmap(self.pixmap)
