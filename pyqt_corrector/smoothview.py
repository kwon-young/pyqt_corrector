from PySide2.QtWidgets import QGraphicsView
from PySide2.QtCore import Signal, Slot, Qt, QPointF, QTimeLine, QRectF
from PySide2.QtGui import QKeyEvent, QWheelEvent, QMouseEvent, QCursor, \
    QVector2D


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
        self._anim = None
        self._wheelEventMousePos = None
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)

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

            if self._anim:
                self._anim.setCurrentTime(0)
            else:
                self._wheelEventMousePos = event.pos()
                self._anim: QTimeLine = QTimeLine(350, self)
                self._anim.setUpdateInterval(20)

                self._anim.valueChanged.connect(self.scalingTime)
                self._anim.finished.connect(self.animFinished)
                self._anim.start()

        else:
            super().wheelEvent(event)

    @Slot()
    def scalingTime(self, x):
        oldPos = self.mapToScene(self._wheelEventMousePos)

        factor = 1.0 + self._numScheduledScalings / 100.0
        self.scale(factor, factor)
        self._numScheduledScalings -= self._numScheduledScalings * x * x

        # compute normalized direction vector from viewport center to cursor
        sceneRect = self.viewport().geometry()
        cursor = QCursor()
        cursorPos = self.mapFromGlobal(cursor.pos())
        vector = QVector2D(cursorPos - sceneRect.center())
        if vector.length() < 5:
            vector = QVector2D(0, 0)
        else:
            vector.normalize()
        vector *= 5 * x

        if factor > 1:
            # drift the viewport so that the point below cursor get closer
            # to the center of the viewport
            newPos = QPointF(self._wheelEventMousePos) - vector.toPointF()
            newPos = newPos.toPoint()
            # drift the cursor to have the sensation that the mouse is tracking
            # the object below the cursor
            newCursorPos = (QPointF(cursorPos) - vector.toPointF()).toPoint()
            cursor.setPos(self.mapToGlobal(newCursorPos))
        else:
            newPos = self._wheelEventMousePos
        newPos = self.mapToScene(newPos)
        delta = newPos - oldPos
        self.translate(delta.x(), delta.y())

    @Slot()
    def animFinished(self):
        del self._anim
        self._anim = None

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
