# -*- coding: utf-8 -*-
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import (
    QgsRectangle, QgsGeometry, QgsWkbTypes, QgsPointXY,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor


class ExtentDrawingTool(QgsMapTool):
    """Rubber-band rectangle tool.  Calls callback(xmin, ymin, xmax, ymax)
    in EPSG:4326 when the user releases the mouse."""

    def __init__(self, canvas, callback):
        super().__init__(canvas)
        self.canvas      = canvas
        self.callback    = callback
        self.start_point = None

        self.rb = QgsRubberBand(self.canvas, QgsWkbTypes.GeometryType.PolygonGeometry)
        self.rb.setWidth(2)
        self.rb.setFillColor(QColor(10, 100, 255, 60))
        self.rb.setBrushStyle(Qt.BrushStyle.SolidPattern)
        self.rb.setStrokeColor(QColor(0, 100, 255, 200))

    def canvasPressEvent(self, event):
        self.start_point = self.toMapCoordinates(event.pos())
        self.rb.reset(QgsWkbTypes.GeometryType.PolygonGeometry)

    def canvasMoveEvent(self, event):
        if not self.start_point:
            return
        end  = self.toMapCoordinates(event.pos())
        rect = QgsRectangle(self.start_point, end)
        pts  = [
            QgsPointXY(rect.xMinimum(), rect.yMinimum()),
            QgsPointXY(rect.xMaximum(), rect.yMinimum()),
            QgsPointXY(rect.xMaximum(), rect.yMaximum()),
            QgsPointXY(rect.xMinimum(), rect.yMaximum()),
            QgsPointXY(rect.xMinimum(), rect.yMinimum()),
        ]
        self.rb.setToGeometry(QgsGeometry.fromPolygonXY([pts]), None)

    def canvasReleaseEvent(self, event):
        end  = self.toMapCoordinates(event.pos())
        rect = QgsRectangle(self.start_point, end)
        self.rb.reset(QgsWkbTypes.GeometryType.PolygonGeometry)

        # Transform to EPSG:4326 if the project CRS differs
        src_crs = QgsProject.instance().crs()
        dst_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        if src_crs != dst_crs:
            xform = QgsCoordinateTransform(src_crs, dst_crs, QgsProject.instance())
            rect  = xform.transformBoundingBox(rect)

        self.canvas.unsetMapTool(self)
        self.callback(rect.xMinimum(), rect.yMinimum(),
                      rect.xMaximum(), rect.yMaximum())
