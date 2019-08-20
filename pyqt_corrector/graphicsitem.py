from PySide2.QtWidgets import QGraphicsRectItem, QGraphicsItem, \
    QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent
from PySide2.QtCore import Qt, QMarginsF, QRectF
from PySide2.QtGui import QPainter, QPen, QPainterPath


class ColorRect(QGraphicsRectItem):

    def __init__(self, color, parent=None):
        super().__init__(parent)

        self.color = color
        self.penWidth = 1

    def setColor(self, color):
        self.color = color
        self.update(self.boundingRect())

    def paint(self, painter: QPainter, option, widget):
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


class ResizableRect(ColorRect):

    """Resizable rect showing a bounding box"""

    def __init__(self, signalHandler, tabIndex, tabName, rowIndex, page, label, box,
                 color, parent=None):
        """Constructor

        """
        super().__init__(color, parent)
        # handle starting at topleft, going clockwise
        self.signalHandler = signalHandler
        self.handles = [ColorRect(color, self) for _ in range(8)]
        self.setVisible(True)
        self.setAcceptHoverEvents(True)
        self.setFiltersChildEvents(True)
        self.setFlags(
            QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable)
        self.setHandlesVisible(False)
        self.handleSelected = None
        self.buttonDownRect = None
        self.setRect(box)
        self.setToolTip(f"{tabName}: {label}")
        self.tabIndex = tabIndex
        self.rowIndex = rowIndex
        self.page = page
        self.label = label
        self.tabName = tabName

    def __str__(self):
        return f"ResizableRect: {self.tabIndex} {self.tabName} {self.rowIndex}"

    def setTabName(self, tabName):
        self.tabName = tabName
        self.setToolTip(f"{self.tabName}: {self.label}")

    def setLabel(self, label):
        self.label = label
        self.setToolTip(f"{self.tabName}: {self.label}")

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
        self.signalHandler.boxPressed.emit(
            self.tabIndex, self.rowIndex)
        self.buttonDownRect = QRectF(self.rect())
        for i, handle in enumerate(self.handles):
            if handle.boundingRect().contains(event.pos()):
                if self.handleSelected is None:
                    self.handleSelected = i

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
        self.signalHandler.boxChanged.emit(
            self.tabIndex, self.rowIndex, new_box)

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

    @classmethod
    def fromProp(cls, prop):
        return cls(
            prop.signalHandler,
            prop.tabIndex,
            prop.tabName,
            prop.rowIndex,
            prop.page,
            prop.label,
            prop.box,
            prop.color)


class RectProp():

    def __init__(self, rect: ResizableRect):
        self.signalHandler = rect.signalHandler
        self.tabIndex = rect.tabIndex
        self.tabName = rect.tabName
        self.rowIndex = rect.rowIndex
        self.page = rect.page
        self.label = rect.label
        self.box = rect.rect()
        self.color = rect.color
