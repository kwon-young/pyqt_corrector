from PySide2.QtWidgets import QGraphicsView
from PySide2.QtCore import Signal, Slot, Qt, QPointF, QTimeLine, QRectF
from PySide2.QtGui import QKeyEvent, QWheelEvent, QMouseEvent


class SmoothView(QGraphicsView):

    """QGraphicsView with smooth scrolling"""

    mouseMoved = Signal(str)
    viewportMoved = Signal(QRectF, QRectF)

    def __init__(self, parent=None):
        """Constructor

        """
        super().__init__(parent)

        self._numScheduledScalings = 0
        self._maxScaling = 20
        self._zoomState = False
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setMouseTracking(True)
        self.prevSceneRect = None
        self.toggleMove = False

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self._zoomState = True

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self._zoomState = False

    def wheelEvent(self, event: QWheelEvent):
        numDegrees = QPointF(event.angleDelta()) / 8.
        # scroll degree wise
        numSteps = numDegrees / 15.  # see QWheelEvent documentation
        if self._zoomState is True:
            if abs(self._numScheduledScalings) < self._maxScaling:
                self._numScheduledScalings += numSteps.y()
            # if user moved the wheel in another direction, we reset previously scheduled scalings
            if self._numScheduledScalings * numSteps.y() < 0:
                self._numScheduledScalings = min(numSteps.y(),
                                                 self._maxScaling)

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

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.prevSceneRect = self.mapToScene(
                self.viewport().geometry()).boundingRect()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        newPos = self.mapToScene(event.pos())
        self.mouseMoved.emit(f"({int(newPos.x())}, {int(newPos.y())})")
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        sceneRect = self.mapToScene(self.viewport().geometry()).boundingRect()
        if self.prevSceneRect is not None and not (
                self.prevSceneRect.top() == sceneRect.top()
                and self.prevSceneRect.left() == sceneRect.left()
                and self.prevSceneRect.bottom() == sceneRect.bottom()
                and self.prevSceneRect.right() == sceneRect.right()):
            self.viewportMoved.emit(sceneRect, self.prevSceneRect)
        super().mouseReleaseEvent(event)
