from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Slot
from PySide2.QtCore import Qt

from scene import Scene
from lights import Light
from objects import Camera, GltfObject
from input import InputController

import glm
import time

class GLWidget(QtWidgets.QOpenGLWidget):
    def __init__(self, scene: Scene, parent: QtWidgets.QWidget = None):
        super(GLWidget, self).__init__(parent)
        self.scene = scene
        self.last_time = time.time()
        self.render_time = 0
        self.render_frames = 0

    def initializeGL(self):
        self.scene.init_gl(self.width(), self.height())

    def paintGL(self):
        start = time.time()
        self.scene.render(self.width(), self.height())
        end = time.time()
        self.render_time += (end - start)
        self.render_frames += 1
        if end > self.last_time + 1:
            print('Average render time: %ims' % (self.render_time * 1000 / self.render_frames))
            self.render_time = 0
            self.render_frames = 0
            self.last_time = end

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, scene: Scene, parent: QtWidgets.QWidget = None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.scene = scene
        self.input_controller = InputController(scene)
        self.gl_widget = GLWidget(scene)
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

    def keyPressEvent(self, event: QtCore.QEvent):
        self.keys[event.key()] = True
        if event.key() == Qt.Key_Escape:
            self.grabbed_mouse = False
            self.setMouseTracking(False)
            self.releaseMouse()

    def keyReleaseEvent(self, event: QtCore.QEvent):
        self.keys[event.key()] = False

    def mousePressEvent(self, event: QtCore.QEvent):
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

# https://sketchfab.com/3d-models/lowpoly-fps-tdm-game-map-d41a19f699ea421a9aa32b407cb7537b
gltf_object = GltfObject('lowpoly__fps__tdm__game__map.glb')

# https://sketchfab.com/3d-models/viking-room-6d61f7f0b597490aab7afa003e4ec725
# gltf_object = GltfObject('viking_room.glb')

camera = Camera(glm.vec3(0, 0, .5), 50)
light = Light(glm.vec3(8, 11, 8))
scene = Scene([gltf_object], camera, light)

window = MainWindow(scene)
window.show()

app.exec_()