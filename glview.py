from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Slot
from PySide2.QtCore import Qt

from OpenGL import GL
import numpy as np
from pygltflib import GLTF2
from PySide2.support import VoidPtr

vertex_source = '''
#version 130
attribute highp vec3 position;
attribute highp vec3 normal;
uniform mat4 projection_transform;
uniform mat4 view_transform;
uniform mat4 model_transform;
varying float shade;

void main()
{
    gl_Position = projection_transform * view_transform * model_transform * vec4(position, 1);
    shade = max(dot(view_transform * model_transform * vec4(normal, 0), vec4(0, 0, 1, 0)), 0);
}
'''

fragment_source = '''
#version 130

uniform vec4 color;

varying float shade;

void main()
{
    gl_FragColor = shade * color;
}
'''

class GLWidget(QtWidgets.QOpenGLWidget, QtGui.QOpenGLFunctions):
    def __init__(self, gltf, parent=None):
        QtWidgets.QOpenGLWidget.__init__(self, parent)
        QtGui.QOpenGLFunctions.__init__(self)
        self.gltf = gltf
        self.yaw = 0
        self.pitch = 0
        self.translate = QtGui.QVector3D(0, .5, 0)
        self.velocity = QtGui.QVector3D()

    def initializeGL(self):
        self.initializeOpenGLFunctions()

        self.glEnable(GL.GL_DEPTH_TEST)
        self.glEnable(GL.GL_CULL_FACE)
        self.glClearColor(.2, .2, .2, 1)

        self.program = QtGui.QOpenGLShaderProgram()
        
        vertex_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Vertex, self)
        vertex_shader.compileSourceCode(vertex_source)
        self.program.addShader(vertex_shader)

        fragment_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Fragment, self)
        fragment_shader.compileSourceCode(fragment_source)
        self.program.addShader(fragment_shader)
        self.program.link()

        self.init_scene()

    def draw_mesh(self, mesh, model_transform):
        self.program.setUniformValue('model_transform', model_transform)

        for primitive in mesh.primitives:
            material = self.gltf.materials[primitive.material]
            c = material.pbrMetallicRoughness.baseColorFactor
            color = QtGui.QColor()
            color.setRgbF(c[0], c[1], c[2], c[3])
            self.program.setUniformValue('color', color)

            accessor = self.gltf.accessors[primitive.attributes.POSITION]
            buffer = self.buffers[accessor.bufferView]
            buffer.bind()
            self.program.setAttributeBuffer('position', GL.GL_FLOAT, accessor.byteOffset, 3)
            buffer.release()
        
            accessor = self.gltf.accessors[primitive.attributes.NORMAL]
            buffer = self.buffers[accessor.bufferView]
            buffer.bind()
            self.program.setAttributeBuffer('normal', GL.GL_FLOAT, accessor.byteOffset, 3)
            buffer.release()
        
            accessor = self.gltf.accessors[primitive.indices]
            buffer = self.buffers[accessor.bufferView]
            buffer.bind()
            self.glDrawElements(GL.GL_TRIANGLES, accessor.count, GL.GL_UNSIGNED_INT, VoidPtr(int(accessor.byteOffset)))
            buffer.release()

    def draw_node(self, node, model_transform):
        if node.mesh:
            self.draw_mesh(self.gltf.meshes[node.mesh], model_transform)
        
        for n in node.children:
            child_node = self.gltf.nodes[n]
            matrix = model_transform
            if child_node.matrix:
                matrix = QtGui.QMatrix4x4(*child_node.matrix).transposed() * matrix
            
            self.draw_node(child_node, matrix)

    def paintGL(self):
        self.glClear(GL.GL_COLOR_BUFFER_BIT or GL.GL_DEPTH_BUFFER_BIT)

        self.program.bind()

        projection_transform = QtGui.QMatrix4x4()
        projection_transform.perspective(50, 1, .1, 100)
        
        view_transform = QtGui.QMatrix4x4()
        view_transform.rotate(self.pitch, 1, 0, 0)
        view_transform.rotate(self.yaw, 0, 1, 0)
        view_transform.translate(-self.translate)
        view_transform.rotate(-90, 1, 0, 0)
        
        self.program.setUniformValue('projection_transform', projection_transform)
        self.program.setUniformValue('view_transform', view_transform)

        model_transform = QtGui.QMatrix4x4()

        self.program.enableAttributeArray('position')
        self.program.enableAttributeArray('normal')
        
        scene = self.gltf.scenes[self.gltf.scene]
        for node in scene.nodes:
            self.draw_node(self.gltf.nodes[node], model_transform)

        self.program.disableAttributeArray('position')
        self.program.disableAttributeArray('normal')
        
        self.program.release()

    def init_scene(self):
        buffer = self.gltf.buffers[0]
        data = self.gltf.get_data_from_buffer_uri(buffer.uri)
        data = memoryview(data)
        self.buffers = []
        i = 0
        for view in self.gltf.bufferViews:
            type = QtGui.QOpenGLBuffer.Type.IndexBuffer if i == 0 else QtGui.QOpenGLBuffer.Type.VertexBuffer
            buffer = QtGui.QOpenGLBuffer(type)
            buffer.create()
            buffer.bind()
            buffer.allocate(data[view.byteOffset:view.byteOffset + view.byteLength], view.byteLength)
            self.buffers.append(buffer)
            i += 1

    def move(self, accel, delta_time):
        matrix = QtGui.QMatrix4x4()
        matrix.rotate(self.yaw, 0, 1, 0)

        drag = 15.0
        drag_vector = matrix.mapVector(-self.velocity * drag)

        if accel.x() == 0: accel.setX(drag_vector.x())
        if accel.y() == 0: accel.setY(drag_vector.y())
        if accel.z() == 0: accel.setZ(drag_vector.z())

        matrix = QtGui.QMatrix4x4()
        matrix.rotate(-self.yaw, 0, 1, 0)

        self.velocity += matrix.mapVector(accel * delta_time)
        max_velocity = 7.0
        if self.velocity.length() > max_velocity:
            self.velocity.normalize()
            self.velocity *= max_velocity
        self.translate += self.velocity * delta_time

    def rotate(self, yaw, pitch):
        self.yaw += yaw
        self.pitch += pitch
        self.pitch = min(max(self.pitch, -45), 45)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.gltf = GLTF2().load('lowpoly__fps__tdm__game__map.glb')
        self.gl_widget = GLWidget(self.gltf)
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
        move = QtGui.QVector3D()
        key_map = {
            Qt.Key_W: (0, 0, -1),
            Qt.Key_A: (-1, 0, 0),
            Qt.Key_S: (0, 0, 1),
            Qt.Key_D: (1, 0, 0),
            Qt.Key_Q: (0, -1, 0),
            Qt.Key_E: (0, 1, 0),
        }

        delta_time = self.elapsed_timer.elapsed()
        move_speed = 15.0

        for key in key_map:
            if(self.keys.get(key, False)):
                move = move + QtGui.QVector3D(*key_map[key])
        move = move * move_speed

        self.gl_widget.move(move, delta_time / 1000.0)

        if self.grabbed_mouse:
            mouse_delta = self.mapFromGlobal(QtGui.QCursor.pos()) - QtCore.QPoint(self.width() / 2, self.height() / 2)
            QtGui.QCursor.setPos(self.mapToGlobal(QtCore.QPoint(self.width() / 2, self.height() / 2)))

            rotate_speed = 0.05
            yaw = mouse_delta.x() * rotate_speed
            pitch = mouse_delta.y() * rotate_speed

            self.gl_widget.rotate(yaw, pitch)

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

window = MainWindow()
window.show()

app.exec_()