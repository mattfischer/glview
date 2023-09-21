from PySide2 import QtCore, QtWidgets, QtGui
from OpenGL import GL
import numpy as np
from pygltflib import GLTF2
from PySide2.support import VoidPtr
import struct

vertex_source = '''
#version 130
attribute highp vec3 position;
uniform mat4 transform;
uniform mat4 object_transform;

void main()
{
    gl_Position = transform * object_transform * vec4(position, 1);
}
'''

fragment_source = '''
#version 130

uniform vec4 color;
void main()
{
    gl_FragColor = color;
}
'''

class GLWidget(QtWidgets.QOpenGLWidget, QtGui.QOpenGLFunctions):
    def __init__(self, gltf, parent=None):
        QtWidgets.QOpenGLWidget.__init__(self, parent)
        QtGui.QOpenGLFunctions.__init__(self)
        self.gltf = gltf
        self.angle = 0

    def initializeGL(self):
        self.initializeOpenGLFunctions()
        self.program = QtGui.QOpenGLShaderProgram()
        
        vertex_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Vertex, self)
        vertex_shader.compileSourceCode(vertex_source)
        self.program.addShader(vertex_shader)

        fragment_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Fragment, self)
        fragment_shader.compileSourceCode(fragment_source)
        self.program.addShader(fragment_shader)
        self.program.link()

        self.init_scene()

    def draw_mesh(self, mesh, object_transform):
        self.program.setUniformValue('object_transform', object_transform)

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
        
            accessor = self.gltf.accessors[primitive.indices]
            buffer = self.buffers[accessor.bufferView]
            buffer.bind()
            self.glDrawElements(GL.GL_TRIANGLES, accessor.count, GL.GL_UNSIGNED_INT, VoidPtr(int(accessor.byteOffset)))
            buffer.release()

    def draw_node(self, node, object_transform):
        if node.mesh:
            self.draw_mesh(self.gltf.meshes[node.mesh], object_transform)
        
        for n in node.children:
            child_node = self.gltf.nodes[n]
            matrix = object_transform
            if child_node.matrix:
                matrix = QtGui.QMatrix4x4(*child_node.matrix).transposed() * matrix
            
            self.draw_node(child_node, matrix)

    def paintGL(self):
        self.angle += 1
        self.program.bind()

        transform = QtGui.QMatrix4x4()
        transform.perspective(50, 1, .1, 100)
        transform.translate(0, 2, -30)
        transform.rotate(self.angle, 0, 1, 0)
        self.program.setUniformValue('transform', transform)

        object_transform = QtGui.QMatrix4x4()

        self.program.enableAttributeArray('position')
        
        scene = self.gltf.scenes[self.gltf.scene]
        for node in scene.nodes:
            self.draw_node(self.gltf.nodes[node], object_transform)

        self.program.disableAttributeArray('position')
        
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

gltf = GLTF2().load('lowpoly__fps__tdm__game__map.glb')

app = QtWidgets.QApplication()
window = QtWidgets.QMainWindow()
gl_widget = GLWidget(gltf)
window.setCentralWidget(gl_widget)
window.setFixedSize(1024, 768)
window.show()

def on_timer():
    gl_widget.update()

timer = QtCore.QTimer()
timer.timeout.connect(on_timer)
timer.start(30)

app.exec_()