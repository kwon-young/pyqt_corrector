import os
import glob
from itertools import zip_longest
from PySide2.QtWidgets import QWidget, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QStyleOptionGraphicsItem, QCommonStyle, QStyle, QGraphicsSceneHoverEvent, QGraphicsItem, QGraphicsSceneMouseEvent
from PySide2.QtCore import Slot, Signal, QModelIndex, Qt, QTimeLine, QPointF, QRect, QMarginsF, QRectF, QSizeF
from PySide2.QtGui import QPixmap, QWheelEvent, QKeyEvent, QMouseEvent, QResizeEvent, QPainter, QPainterPath
from pyqt_corrector.models import TableModel


class SmoothView(QGraphicsView):

    """QGraphicsView with smooth scrolling"""

    mouseMoved = Signal(str)

    def __init__(self, parent=None):
        """Constructor

        """
        super().__init__(parent)

        self._numScheduledScalings = 0
        self._maxScaling = 4
        self._zoomState = False
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setMouseTracking(True)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self._zoomState = True

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self._zoomState = False

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

    def mouseMoveEvent(self, event: QMouseEvent):
        newPos = self.mapToScene(event.pos())
        self.mouseMoved.emit(f"({int(newPos.x())}, {int(newPos.y())})")
        super().mouseMoveEvent(event)


class ResizableRect(QGraphicsRectItem):

    """Resizable rect showing a bounding box"""

    def __init__(self, parent=None):
        """Constructor

        """
        super().__init__(parent)
        # handle starting at topleft, going clockwise
        self.handles = [QGraphicsRectItem(self) for _ in range(8)]
        self.setVisible(True)
        self.setAcceptHoverEvents(True)
        self.setFiltersChildEvents(True)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setHandlesVisible(False)
        for handle in self.handles:
            handle.setAcceptHoverEvents(True)
        self.handleSelected = None

    def handleSize(self):
        box = self.rect()
        width, height = box.width(), box.height()
        handle_size = min(width / 3, height / 3)
        return handle_size

    def setHandlesPos(self):
        box = self.rect()
        handle_size = self.handleSize()
        half_handle_size = handle_size / 2
        self.handles[0].setRect(
            box.left() - half_handle_size, box.top() - half_handle_size,
            handle_size, handle_size)
        self.handles[1].setRect(
            box.center().x() - half_handle_size, box.top() - half_handle_size,
            handle_size, handle_size)
        self.handles[2].setRect(
            box.right() - half_handle_size, box.top() - half_handle_size,
            handle_size, handle_size)
        self.handles[3].setRect(
            box.right() - half_handle_size, box.center().y() -
            half_handle_size, handle_size, handle_size)
        self.handles[4].setRect(
            box.right() - half_handle_size, box.bottom() - half_handle_size,
            handle_size, handle_size)
        self.handles[5].setRect(
            box.center().x() - half_handle_size, box.bottom() -
            half_handle_size, handle_size, handle_size)
        self.handles[6].setRect(
            box.left() - half_handle_size, box.bottom() - half_handle_size,
            handle_size, handle_size)
        self.handles[7].setRect(
            box.left() - half_handle_size, box.center().y() - half_handle_size,
            handle_size, handle_size)
        return

    def setRect(self, *args):
        super().setRect(*args)
        self.setHandlesPos()

    def setHandlesVisible(self, state):
        for handle in self.handles:
            handle.setVisible(state)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent):
        self.setHandlesVisible(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent):
        self.setHandlesVisible(False)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        for i, handle in enumerate(self.handles):
            if handle.isUnderMouse():
                self.handleSelected = i
                return

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self.handleSelected is not None:
            self.handleSelected = None
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        if self.handleSelected is None:
            super().mouseMoveEvent(event)
            return
        box = self.rect()
        pos = event.pos()
        if self.handleSelected == 0:
            new_size = box.bottomRight() - pos
            width = max(new_size.x(), 1)
            height = max(new_size.y(), 1)
            left = min(pos.x(), box.right())
            top = min(pos.y(), box.bottom())
            new_box = QRectF(left, top, width, height)
        elif self.handleSelected == 1:
            height = max(box.bottom() - pos.y(), 1)
            top = min(pos.y(), box.bottom())
            new_box = QRectF(box.left(), top, box.width(), height)
        elif self.handleSelected == 2:
            top = min(pos.y(), box.bottom())
            width = max(pos.x() - box.left(), 1)
            height = max(box.bottom() - pos.y(), 1)
            new_box = QRectF(box.left(), top, width, height)
        elif self.handleSelected == 3:
            width = max(pos.x() - box.left(), 1)
            new_box = QRectF(box.left(), box.top(), width, box.height())
        elif self.handleSelected == 4:
            new_size = pos - box.topLeft()
            width = max(new_size.x(), 1)
            height = max(new_size.y(), 1)
            new_box = QRectF(box.left(), box.top(), width, height)
        elif self.handleSelected == 5:
            width = max(pos.x() - box.left(), 1)
            new_box = QRectF(box.left(), box.top(), box.width(), height)
        elif self.handleSelected == 6:
            left = min(pos.x(), box.right())
            width = max(box.right() - pos.x(), 1)
            height = max(pos.y() - box.top(), 1)
            new_box = QRectF(left, box.top(), width, height)
        elif self.handleSelected == 7:
            left = min(pos.x(), box.right())
            width = max(box.right() - pos.x(), 1)
            new_box = QRectF(left, box.top(), width, box.height())
        self.setRect(new_box)
        self.setHandlesPos()

    def boundingRect(self):
        box = self.rect()
        half_handle_size = self.handleSize() / 2
        margin = QMarginsF(*([half_handle_size] * 4))
        return box + margin

    def shape(self):
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path


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
        self.graphicsPixmapItem = None
        self.resizableRects = []

    @Slot()
    def update(self, index: QModelIndex):
        """Update image and bounding boxes from new index"""
        data: TableModel = index.model()
        page, label, boxes = data.data(index, Qt.UserRole)
        path = os.path.join(self.directory, f"*{page}*")
        names = glob.glob(path)
        if not names:
            self.imageNotFound.emit(f"no image found in {path}")
            return
        self.imageName = names[0]
        self.pixmap = QPixmap(self.imageName)
        self.graphicsPixmapItem = self.scene.addPixmap(self.pixmap)

        if boxes:
            self.drawBoxes(boxes)

    def drawBoxes(self, boxes):
        newRubberBands = []
        for box, resizableRect in zip_longest(
                boxes, self.resizableRects):
            if box is None:
                # means there are more resizableRects than boxes to draw
                self.scene.removeItem(resizableRect)
            elif resizableRect is None:
                # means there are more boxes to draw than resizableRects
                resizableRect = ResizableRect(self.graphicsPixmapItem)
                resizableRect.setRect(box)
                newRubberBands.append(resizableRect)
            else:
                # existing box and resizableRect
                resizableRect.setRect(box)
