from PySide2.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent, \
    QGraphicsPixmapItem, QComboBox
from PySide2.QtCore import QObject, Signal, QRectF, Qt, QModelIndex, QSizeF
from PySide2.QtGui import QPixmap
from pyqt_corrector.graphicsitem import ResizableRect
from pyqt_corrector.tabwidget import TabWidget


class SignalHandler(QObject):

    """Simple QObject relaying signal on behalf of QGraphicsItem"""

    boxPressed = Signal(int, int)
    boxChanged = Signal(int, int, QRectF)
    boxCreated = Signal(ResizableRect)


class GraphicsScene(QGraphicsScene):

    """Custom GraphicsScene"""

    signalHandler = SignalHandler()

    def __init__(self, parent=None):
        """Constructor
        """
        super().__init__(parent)
        self.tabWidget: TabWidget = None
        self.comboBox: QComboBox = None
        self.page = ""

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() == Qt.LeftButton and \
                event.modifiers() & Qt.ControlModifier:
            tabIndex = self.tabWidget.currentIndex()
            tabName = self.tabWidget.tabText(tabIndex)
            rowIndex = self.tabWidget.getCurrentTableModel().rowCount(
                QModelIndex())
            label = self.comboBox.currentText()
            box = QRectF(event.buttonDownScenePos(Qt.LeftButton), QSizeF(1, 1))
            color = self.tabWidget.color_map(tabIndex)[label]
            rect = self.addBox(tabIndex, tabName, rowIndex, self.page, label,
                               box, color)
            rect.handleSelected = 4
            self.signalHandler.boxCreated.emit(rect)
        super().mousePressEvent(event)

    def addItem(self, item):
        # num = len(self.items())
        # print("PRE addItem:", len(self.items()))
        if isinstance(item, ResizableRect):
            item.signalHandler = self.signalHandler
        super().addItem(item)
        # print("POST addItem:", len(self.items()))
        # assert len(self.items()) == num + 1 + len(item.childItems()), item

    def setPage(self, page, pixmap: QPixmap):
        # print("PRE setPage:", len(self.items()))
        if self.page != page:
            self.page = page
            backgroundItem: QGraphicsPixmapItem = self.addPixmap(pixmap)
            backgroundItem.setZValue(-1)
            # print("POST setPage True:", len(self.items()))
            return True
        # print("POST setPage False:", len(self.items()))
        return False

    def addBox(self, *args):
        # print("PRE addBox:", len(self.items()))
        rect = ResizableRect(self.signalHandler, *args)
        self.addItem(rect)
        # print("POST addBox:", len(self.items()))
        return rect

    def insertBox(self, tabIndex, rowIndex, box):
        for b in self.boxes():
            if b.tabIndex == tabIndex and b.rowIndex >= rowIndex:
                b.rowIndex += 1
        self.addItem(box)

    def removeBox(self, tabIndex, rowIndex):
        res = None
        for box in self.boxes():
            if box.tabIndex == tabIndex and box.rowIndex == rowIndex:
                self.removeItem(box)
                res = box
            elif box.tabIndex == tabIndex and box.rowIndex > rowIndex:
                box.rowIndex -= 1
        return res

    def boxes(self):
        for item in self.items():
            if isinstance(item, ResizableRect):
                yield item

    def removeAllItems(self):
        # print("PRE removeAllItems:", len(self.items()))
        for item in self.items():
            self.removeItem(item)
        # print("POST removeAllItems:", len(self.items()))
        self.page = ""

    def removeTabItems(self, tabIndex):
        removedItems = []
        for item in self.boxes():
            if item.tabIndex == tabIndex:
                self.removeItem(item)
                removedItems.append(item)

        return removedItems

    def changeTabIndices(self, index_map):
        for item in self.boxes():
            item.tabIndex = index_map[item.tabIndex]

    def changeTabColor(self, tabIndex, color_map):
        for item in self.boxes():
            if item.tabIndex == tabIndex:
                item.setColor(color_map[item.label])

    def box(self, tabIndex: int, rowIndex: int):
        for item in self.boxes():
            if item.tabIndex == tabIndex and item.rowIndex == rowIndex:
                return item
        raise "Box not found"
