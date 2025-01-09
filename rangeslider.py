from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QRect

from PyQt5.QtCore import pyqtSignal

class RangeSlider(QWidget):

    # Signal emitted when the range values change
    rangeChanged = pyqtSignal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.low_value = 20
        self.high_value = 80
        self.range_min = 0
        self.range_max = 100
        self.slider_width = 10
        self.active_handle = None

    def paintEvent(self, event):
        painter = QPainter(self)
        width = self.width()
        height = self.height()

        # Draw background bar
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(0, height // 2 - 5, width, 10)

        # Draw range
        low_pos = int(self.value_to_pos(self.low_value))  # Convert to int
        high_pos = int(self.value_to_pos(self.high_value))  # Convert to int
        painter.setBrush(QColor(100, 100, 255))
        painter.drawRect(low_pos, height // 2 - 5, high_pos - low_pos, 10)

        # Draw handles
        painter.setBrush(QColor(255, 100, 100))
        painter.drawEllipse(
            low_pos - self.slider_width // 2,
            height // 2 - self.slider_width // 2,
            self.slider_width,
            self.slider_width,
        )
        painter.drawEllipse(
            high_pos - self.slider_width // 2,
            height // 2 - self.slider_width // 2,
            self.slider_width,
            self.slider_width,
        )

        # Add labels for low and high values
        painter.setPen(QColor(0, 0, 0))  # Black color for text
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)

        # Low value label
        painter.drawText(
            low_pos - 20,  # Position slightly to the left of the low handle
            height // 2 - 15,  # Above the handle
            f"{self.low_value}",
        )

        # High value label
        painter.drawText(
            high_pos + 5,  # Position slightly to the right of the high handle
            height // 2 - 15,  # Above the handle
            f"{self.high_value}",
        )
        
    def mousePressEvent(self, event):
        pos = event.x()
        low_pos = self.value_to_pos(self.low_value)
        high_pos = self.value_to_pos(self.high_value)

        if abs(pos - low_pos) < self.slider_width:
            self.active_handle = "low"
            self.rangeChanged.emit(self.low_value, self.high_value)
        elif abs(pos - high_pos) < self.slider_width:
            self.active_handle = "high"
            self.rangeChanged.emit(self.low_value, self.high_value)

    def mouseMoveEvent(self, event):
        if self.active_handle is None:
            return

        pos = event.x()
        value = self.pos_to_value(pos)

        if self.active_handle == "low":
            self.low_value = max(self.range_min, min(self.high_value, value))
        elif self.active_handle == "high":
            self.high_value = min(self.range_max, max(self.low_value, value))

        self.update()

    def mouseReleaseEvent(self, event):
        self.active_handle = None

    def value_to_pos(self, value):
        return (value - self.range_min) / (self.range_max - self.range_min) * self.width()

    def pos_to_value(self, pos):
        return int(pos / self.width() * (self.range_max - self.range_min) + self.range_min)

if __name__ == "__main__":
    app = QApplication([])
    window = RangeSlider()
    window.resize(400, 100)
    window.show()
    app.exec_()
