import os
import glob
from itertools import zip_longest
import seaborn
from PySide2.QtWidgets import QWidget, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QStyleOptionGraphicsItem, QCommonStyle, QStyle, QGraphicsSceneHoverEvent, QGraphicsItem, QGraphicsSceneMouseEvent, QGraphicsPixmapItem
from PySide2.QtCore import Slot, Signal, QModelIndex, Qt, QTimeLine, QPointF, QRect, QMarginsF, QRectF, QSizeF
from PySide2.QtGui import QPixmap, QWheelEvent, QKeyEvent, QMouseEvent, QResizeEvent, QPainter, QPainterPath, QColor, QPen
from pyqt_corrector.models import TableModel


class SmoothView(QGraphicsView):

    """QGraphicsView with smooth scrolling"""

    mouseMoved = Signal(str)

    def __init__(self, parent=None):
        """Constructor

        """
        super().__init__(parent)

        self._numScheduledScalings = 0
        self._maxScaling = 20
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


class ColorRect(QGraphicsRectItem):

    """Rect with configurable color"""

    def __init__(self, parent):
        """Constructor

        """
        super().__init__(parent)

        self.color = None

    def setColor(self, color):
        self.color = color

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: QWidget):
        painter.setPen(QPen(self.color, 3))
        painter.drawRect(self.rect())


class ResizableRect(ColorRect):

    """Resizable rect showing a bounding box"""

    def __init__(self, parent=None):
        """Constructor

        """
        super().__init__(parent)
        # handle starting at topleft, going clockwise
        self.handles = [ColorRect(self) for _ in range(8)]
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

    def setColor(self, color):
        self.color = color
        for handle in self.handles:
            handle.setColor(color)

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

    message = Signal(str)

    def __init__(self, parent):
        """Constructor

        :parent: TODO

        """
        super().__init__(parent)

        self.scene = QGraphicsScene()
        self.scene.clear()

        self.view = SmoothView(self.scene)

        self.directory = None
        self.page = None
        self.graphicsPixmapItem = QGraphicsPixmapItem()
        self.scene.addItem(self.graphicsPixmapItem)
        self.perModelResizableRects = {}
        self.dataModels = []
        self._dataNames = []
        self.tableDatas = []

    @property
    def dataNames(self):
        return self._dataNames

    @dataNames.setter
    def dataNames(self, dataNames):
        self._dataNames = dataNames
        self.perModelResizableRects = {name: [] for name in dataNames}

    @Slot()
    def update(self, index: QModelIndex):
        """Update image and bounding boxes from new index"""
        page = index.model().pageAtIndex(index)

        if page != self.page:
            self.page = page
            path = os.path.join(self.directory, f"*{page}*")
            names = glob.glob(path)
            if not names:
                self.message.emit(f"no image found in {path}")
                return
            self.message.emit(f"loading {os.path.basename(names[0])}")
            pixmap = QPixmap(names[0])
            self.graphicsPixmapItem.setPixmap(pixmap)

            self.tableDatas = [model.pageData(page) for model in self.dataModels]

        labels = set().union(*[tableData["label"]
                               for tableData in self.tableDatas])
        # we use one color per class + one color per not visible tab dataset
        num_colors = len(labels) + len(self.dataModels) - 1
        colors = [QColor(*[int(c * 255) for c in color])
                  for color in seaborn.color_palette(None, num_colors)]
        for i, tableData in enumerate(self.tableDatas):
            curModelIndex = self.dataModels.index(index.model())
            if curModelIndex == i:
                color_map = {label: color
                             for label, color in zip(labels, colors)}
            else:
                num_colors -= 1
                color = colors[num_colors]
                color_map = {label: color for label in labels}

            self.drawBoxes(self._dataNames[i], tableData, color_map)

        boundingRect = index.model().boxAtIndex(index)
        margin_size = min(boundingRect.width(), boundingRect.height()) / 2
        margin = QMarginsF(*([margin_size] * 4))
        self.view.fitInView(boundingRect + margin, Qt.KeepAspectRatio)
        self.view.setFocus()

    def drawBoxes(self, name, data, color_map):
        """draw boxes on top of an image
        This function tries to reuse existing ResizableRect to draw newly given
        boxes. It will dynamically add more boxes and remove unused ones.
        """
        for i, rowData in enumerate(data.values):
            if i >= len(self.perModelResizableRects[name]):
                # means there are more boxes to draw than resizableRects
                resizableRect = ResizableRect()
                self.perModelResizableRects[name].append(resizableRect)
                self.scene.addItem(resizableRect)
            else:
                resizableRect = self.perModelResizableRects[name][i]
            _page, label, box = rowData
            resizableRect.setRect(box)
            resizableRect.setColor(color_map[label])
            resizableRect.setToolTip(f"{name}: {label}")
        # start by removing extraneous resizableBoxes
        for box in self.perModelResizableRects[name][len(data.values):]:
            self.scene.removeItem(box)
        self.perModelResizableRects[name] = self.perModelResizableRects[name][
            :len(data.values)]
