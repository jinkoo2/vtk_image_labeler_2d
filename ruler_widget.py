from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItem
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPen, QColor

import math

class RulerWidget(QGraphicsLineItem):
    def __init__(self, start_point=QPointF(100, 100), end_point=QPointF(200, 100), parent_scene=None):
        super().__init__()
        self.start_point = start_point
        self.end_point = end_point
        self.parent_scene = parent_scene

        # Line appearance
        self.pen = QPen(QColor("blue"))
        self.pen.setWidth(2)
        self.setPen(self.pen)

        # Create draggable handles
        self.start_handle = QGraphicsEllipseItem(-5, -5, 10, 10)
        self.start_handle.setBrush(QColor("red"))
        self.start_handle.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)

        self.end_handle = QGraphicsEllipseItem(-5, -5, 10, 10)
        self.end_handle.setBrush(QColor("red"))
        self.end_handle.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)

        # Distance label
        self.distance_label = QGraphicsTextItem("")
        self.distance_label.setDefaultTextColor(QColor("black"))

        # Add items to the scene
        if self.parent_scene:
            self.parent_scene.addItem(self)
            self.parent_scene.addItem(self.start_handle)
            self.parent_scene.addItem(self.end_handle)
            self.parent_scene.addItem(self.distance_label)

        self.update_positions()

        # Connect position updates
        self.start_handle.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)
        self.end_handle.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)

    def update_positions(self):
        """Update the line, handles, and distance label based on the positions."""
        self.setLine(self.start_point.x(), self.start_point.y(), self.end_point.x(), self.end_point.y())
        self.start_handle.setPos(self.start_point - QPointF(5, 5))
        self.end_handle.setPos(self.end_point - QPointF(5, 5))

        # Update distance label
        self.render_distance_label()

    def render_distance_label(self):
        """Update the distance label."""
        distance = self.calculate_distance()
        midpoint = QPointF(
            (self.start_point.x() + self.end_point.x()) / 2,
            (self.start_point.y() + self.end_point.y()) / 2,
        )
        self.distance_label.setPlainText(f"{distance:.2f}")
        self.distance_label.setPos(midpoint.x(), midpoint.y() - 20)

    def calculate_distance(self):
        """Calculate the distance between the two endpoints."""
        return math.sqrt((self.end_point.x() - self.start_point.x()) ** 2 +
                         (self.end_point.y() - self.start_point.y()) ** 2)

    def itemChange(self, change, value):
        """React to changes in handle positions."""
        if change == QGraphicsItem.ItemPositionChange:
            if self.start_handle.scenePos() != self.start_point - QPointF(5, 5):
                self.start_point = self.start_handle.scenePos() + QPointF(5, 5)
            if self.end_handle.scenePos() != self.end_point - QPointF(5, 5):
                self.end_point = self.end_handle.scenePos() + QPointF(5, 5)
            self.update_positions()
        return super().itemChange(change, value)

    def mouseMoveEvent(self, event):
        print('mouse move event')
        super().mouseMoveEvent(event)