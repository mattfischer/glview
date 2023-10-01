from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Slot
from PySide2.QtCore import Qt

from OpenGL import GL
import numpy as np
import pygltflib
from PySide2.support import VoidPtr
import math

from render import Renderer
from input import InputController

class GLWidget(QtWidgets.QOpenGLWidget):
    def __init__(self, renderer, parent=None):
        super(GLWidget, self).__init__(parent)
        self.renderer = renderer

    def initializeGL(self):
        self.renderer.init_scene()

    def paintGL(self):
        self.renderer.render(self.width(), self.height())

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, renderer, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.renderer = renderer
        self.input_controller = InputController(renderer.camera, renderer.light)
        self.gl_widget = GLWidget(renderer)
        self.setCentralWidget(self.gl_widget)
        self.setFixedSize(1600, 1200)

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.on_timer)
        self.timer.start(16)

        self.keys = {}
        self.grabbed_mouse = False
        self.elapsed_timer = QtCore.QElapsedTimer()
        self.elapsed_timer.start()

    @Slot()
    def on_timer(self):
        delta_time = self.elapsed_timer.elapsed()

        if self.grabbed_mouse:
            mouse_delta = self.mapFromGlobal(QtGui.QCursor.pos()) - QtCore.QPoint(self.width() / 2, self.height() / 2)
            QtGui.QCursor.setPos(self.mapToGlobal(QtCore.QPoint(self.width() / 2, self.height() / 2)))
        else:
            mouse_delta = QtCore.QPoint()

        self.input_controller.update(self.keys, mouse_delta, delta_time / 1000.0)
        self.gl_widget.update()
        self.elapsed_timer.restart()

    def keyPressEvent(self, event):
        self.keys[event.key()] = True
        if event.key() == Qt.Key_Escape:
            self.grabbed_mouse = False
            self.setMouseTracking(False)
            self.releaseMouse()

    def keyReleaseEvent(self, event):
        self.keys[event.key()] = False

    def mousePressEvent(self, event):
        if self.grabbed_mouse:
            self.grabbed_mouse = False
            self.setMouseTracking(False)
            self.releaseMouse()
        else:
            self.grabMouse(QtGui.QCursor(Qt.CursorShape.BlankCursor))
            self.setMouseTracking(True)
            self.grabbed_mouse = True
            QtGui.QCursor.setPos(self.mapToGlobal(QtCore.QPoint(self.width() / 2, self.height() / 2)))

app = QtWidgets.QApplication()

gltf = pygltflib.GLTF2().load('lowpoly__fps__tdm__game__map.glb')
renderer = Renderer(gltf)
window = MainWindow(renderer)
window.show()

app.exec_()