import os
import glob
from itertools import zip_longest
import seaborn
from PySide2.QtWidgets import QWidget, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QStyleOptionGraphicsItem, QCommonStyle, QStyle, QGraphicsSceneHoverEvent, QGraphicsItem, QGraphicsSceneMouseEvent, QGraphicsPixmapItem, QComboBox
from PySide2.QtCore import Slot, Signal, QModelIndex, Qt, QTimeLine, QPointF, QRect, QMarginsF, QRectF, QSizeF, QObject
from PySide2.QtGui import QPixmap, QWheelEvent, QKeyEvent, QMouseEvent, QResizeEvent, QPainter, QPainterPath, QColor, QPen
from pyqt_corrector.models import TableModel


class LabelComboBox(QComboBox):

    """Combobox containing current object label"""

    def __init__(self, parent=None):
        """constructor

        """
        super().__init__(parent)
        self.row = -1


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
        self.penWidth = 1

    def setColor(self, color):
        self.color = color
        self.update(self.boundingRect())

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem,
              widget: QWidget):
        pen = QPen(self.color, self.penWidth)
        if self.isSelected():
            pen.setStyle(Qt.DashLine)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawRect(self.rect())

    def boundingRect(self):
        box = self.rect()
        viewBox = self.mapRectFromScene(box)
        margin = QMarginsF(*([self.penWidth] * 4))
        viewBox += margin
        box = self.mapRectToScene(viewBox)
        return box

class SignalHandler(QObject):

    """Simple QObject relaying signal on behalf of QGraphicsItem"""

    boxPressed = Signal(str, int)
    boxChanged = Signal(str, int, QRectF)

    def __init__(self, parent=None):
        """Constructor """
        super().__init__(parent)


class ResizableRect(ColorRect):

    """Resizable rect showing a bounding box"""

    def __init__(self, signalHandler: SignalHandler, parent=None):
        """Constructor

        """
        super().__init__(parent)
        self.signalHandler = signalHandler
        # handle starting at topleft, going clockwise
        self.handles = [ColorRect(self) for _ in range(8)]
        self.setVisible(True)
        self.setAcceptHoverEvents(True)
        self.setFiltersChildEvents(True)
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setHandlesVisible(False)
        self.handleSelected = None
        self.buttonDownRect = None

    def handleSize(self):
        box = self.rect()
        width, height = box.width(), box.height()
        handle_size = min(width / 3, height / 3)
        return handle_size

    def setHandlesPos(self):
        box = self.rect()
        handle_size = max(self.handleSize(), 2)
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
        for handle in self.handles:
            handle.setColor(color)
        super().setColor(color)

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent):
        self.setHandlesVisible(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent):
        self.setHandlesVisible(False)
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        zValue = self.zValue()
        if zValue > 0:
            self.setSelected(False)
            self.setZValue(zValue - 1)
        else:
            self.setSelected(True)
            self.setZValue(zValue + 1)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        self.signalHandler.boxPressed.emit(self.data(0), self.data(1))
        box = self.rect()
        self.buttonDownRect = QRectF(self.rect())
        for i, handle in enumerate(self.handles):
            if handle.boundingRect().contains(event.pos()):
                self.handleSelected = i
                return

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        if self.handleSelected is not None:
            self.handleSelected = None

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent):
        box = QRectF(self.buttonDownRect)
        pos = event.pos()
        offset = pos - event.buttonDownPos(Qt.LeftButton)
        if self.handleSelected is None:
            box.translate(offset)
            new_box = box
        elif self.handleSelected == 0:
            pos = box.topLeft() + offset
            new_size = box.bottomRight() - pos
            width = max(new_size.x(), 0)
            height = max(new_size.y(), 0)
            left = min(pos.x(), box.right())
            top = min(pos.y(), box.bottom())
            new_box = QRectF(left, top, width, height)
        elif self.handleSelected == 1:
            pos = box.topLeft() + offset
            height = max(box.bottom() - pos.y(), 0)
            top = min(pos.y(), box.bottom())
            new_box = QRectF(box.left(), top, box.width(), height)
        elif self.handleSelected == 2:
            pos = box.topRight() + offset
            top = min(pos.y(), box.bottom())
            width = max(pos.x() - box.left(), 0)
            height = max(box.bottom() - pos.y(), 0)
            new_box = QRectF(box.left(), top, width, height)
        elif self.handleSelected == 3:
            pos = box.topRight() + offset
            width = max(pos.x() - box.left(), 0)
            new_box = QRectF(box.left(), box.top(), width, box.height())
        elif self.handleSelected == 4:
            pos = box.bottomRight() + offset
            new_size = pos - box.topLeft()
            width = max(new_size.x(), 0)
            height = max(new_size.y(), 0)
            new_box = QRectF(box.left(), box.top(), width, height)
        elif self.handleSelected == 5:
            pos = box.bottomRight() + offset
            height = max(pos.y() - box.top(), 0)
            new_box = QRectF(box.left(), box.top(), box.width(), height)
        elif self.handleSelected == 6:
            pos = box.bottomLeft() + offset
            left = min(pos.x(), box.right())
            width = max(box.right() - pos.x(), 0)
            height = max(pos.y() - box.top(), 0)
            new_box = QRectF(left, box.top(), width, height)
        elif self.handleSelected == 7:
            pos = box.bottomLeft() + offset
            left = min(pos.x(), box.right())
            width = max(box.right() - pos.x(), 0)
            new_box = QRectF(left, box.top(), width, box.height())
        new_box = QRectF(round(new_box.left()),
                         round(new_box.top()),
                         round(new_box.width()),
                         round(new_box.height()))
        self.setRect(new_box)
        self.setHandlesPos()
        self.signalHandler.boxChanged.emit(self.data(0), self.data(1), new_box)

    def boundingRect(self):
        rect = super().boundingRect()
        for handle in self.handles:
            rect |= handle.boundingRect()
        return rect

    def shape(self):
        path = QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRect(self.rect())
        for handle in self.handles:
            path.addRect(handle.boundingRect())
        return path


class ImageViewer(QWidget):

    """View an image and multiple annotated boxes"""

    message = Signal(str)
    LabelComboBoxChanged = Signal(int, str)

    def __init__(self, comboBox, parent):
        """Constructor

        :parent: TODO

        """
        super().__init__(parent)

        self.signalHandler = SignalHandler(self)
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
        self.comboBox: LabelComboBox = comboBox
        self.comboBox.activated.connect(self.transmitRowLabel)
        self.curRect = None
        self.color_map = None

    @property
    def dataNames(self):
        return self._dataNames

    @dataNames.setter
    def dataNames(self, dataNames):
        self._dataNames = dataNames
        self.perModelResizableRects = {name: [] for name in dataNames}

    @Slot()
    def updateData(self, topLeft: QModelIndex, bottomRight: QModelIndex,
                   roles):
        self.updateSelect(topLeft)
        # TODO: update corresponding rect color

    @Slot()
    def updateSelect(self, index: QModelIndex):
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

        labels = set().union(*[model.labelSet for model in self.dataModels])
        # we use one color per class + one color per not visible tab dataset
        num_colors = len(labels) + len(self.dataModels) - 1
        colors = [QColor(*[int(c * 255) for c in color])
                  for color in seaborn.color_palette(None, num_colors)]
        curModelIndex = self.dataModels.index(index.model())
        for i, tableData in enumerate(self.tableDatas):
            if curModelIndex == i:
                color_map = {label: color
                             for label, color in zip(labels, colors)}
                self.color_map = color_map.copy()
            else:
                num_colors -= 1
                color = colors[num_colors]
                color_map = {label: color for label in labels}

            self.drawBoxes(self._dataNames[i], tableData, color_map)

        label = index.model().labelAtIndex(index)
        self.comboBox.setCurrentText(label)
        self.comboBox.row = index.row()
        loc = self.tableDatas[curModelIndex].index.get_loc(index.row())
        self.curRect = self.perModelResizableRects[self._dataNames[curModelIndex]][loc]
        boundingRect = self.curRect.boundingRect()
        margin_size = min(boundingRect.width(), boundingRect.height()) / 2
        margin = QMarginsF(*([margin_size] * 4))
        viewRect = boundingRect + margin
        self.view.fitInView(viewRect, Qt.KeepAspectRatio)
        self.view.setFocus()

    def drawBoxes(self, name, data, color_map):
        """draw boxes on top of an image
        This function tries to reuse existing ResizableRect to draw newly given
        boxes. It will dynamically add more boxes and remove unused ones.
        """
        for i, (index, row) in enumerate(data.iterrows()):
            if i >= len(self.perModelResizableRects[name]):
                # means there are more boxes to draw than resizableRects
                resizableRect = ResizableRect(self.signalHandler)
                self.perModelResizableRects[name].append(resizableRect)
                self.scene.addItem(resizableRect)
            else:
                resizableRect = self.perModelResizableRects[name][i]
            resizableRect.setRect(row["box"])
            resizableRect.setColor(color_map[row["label"]])
            resizableRect.setToolTip(f"{name}: {row['label']}")
            resizableRect.setData(0, name)
            resizableRect.setData(1, index)
        # start by removing extraneous resizableBoxes
        for box in self.perModelResizableRects[name][len(data.values):]:
            self.scene.removeItem(box)
        self.perModelResizableRects[name] = self.perModelResizableRects[name][
            :len(data.values)]

    @Slot()
    def transmitRowLabel(self, index: int):
        row = self.comboBox.row
        label = self.comboBox.itemText(index)
        self.LabelComboBoxChanged.emit(row, label)
