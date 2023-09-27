from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Slot
from PySide2.QtCore import Qt

from OpenGL import GL
import numpy as np
import pygltflib
from PySide2.support import VoidPtr
import math

vertex_source = '''
#version 130
attribute highp vec3 position;
attribute highp vec3 normal;
uniform mat4 projection_transform;
uniform mat4 view_transform;
uniform mat4 model_transform;
uniform mat4 light_transform;
varying vec3 frag_pos;
varying vec3 frag_normal;
varying vec4 pos_light_space;

void main()
{
    gl_Position = projection_transform * view_transform * model_transform * vec4(position, 1);
    frag_pos = (model_transform * vec4(position, 1)).xyz;
    pos_light_space = light_transform * vec4(frag_pos, 1);
    frag_normal = normal;
}
'''

fragment_source = '''
#version 130

uniform vec4 color;
uniform vec3 light_position;
uniform sampler2DShadow shadow_texture;

varying vec3 frag_pos;
varying vec3 frag_normal;
varying vec4 pos_light_space;

mat4 shadow_bias = mat4(vec4(.5,  0,  0,  0),
                        vec4( 0, .5,  0,  0),
                        vec4( 0,  0, .5,  0),
                        vec4(.5, .5, .5,  1));
void main()
{
    vec3 light_vec = light_position - frag_pos;
    float light_dist = length(light_vec);
    float shade = max(dot(light_vec / light_dist, frag_normal), 0);
    vec4 light_coord = shadow_bias * pos_light_space;
    float shadow_bias = 0.0005 * light_coord.w / shade;
    float shadow = textureProj(shadow_texture, light_coord - vec4(0, 0, shadow_bias, 0));
    gl_FragColor = (shadow * shade + .25) * color;
}
'''

shadow_vertex_source = '''
#version 130
attribute highp vec3 position;
uniform mat4 projection_transform;
uniform mat4 view_transform;
uniform mat4 model_transform;

void main()
{
    gl_Position = projection_transform * view_transform * model_transform * vec4(position, 1);
}
'''

shadow_fragment_source = '''
#version 130

void main()
{
}
'''

class InputController:
    def __init__(self, camera, light):
        self.camera = camera
        self.light = light

    def update(self, keys, mouse_delta, delta_time):
        rotate_speed = 0.05
        self.camera.orientation += rotate_speed * QtGui.QVector3D(mouse_delta.y(), mouse_delta.x(), 0)
        self.camera.orientation.setX(min(max(self.camera.orientation.x(), -45), 45))

        light_dirs = QtGui.QVector3D()
        light_key_map = {
            Qt.Key_I: (0, 1, 0),
            Qt.Key_J: (-1, 0, 0),
            Qt.Key_K: (0, -1, 0),
            Qt.Key_L: (1, 0, 0),
            Qt.Key_U: (0, 0, -1),
            Qt.Key_O: (0, 0, 1),
        }
        light_moved = False
        for key in light_key_map:
            if(keys.get(key, False)):
                light_dirs = light_dirs + QtGui.QVector3D(*light_key_map[key])
                light_moved = True

        light_velocity = 10.0
        self.light.position += light_dirs * light_velocity * delta_time
        self.light.need_shadow_render = light_moved

        dirs = QtGui.QVector3D()
        key_map = {
            Qt.Key_W: (0, 1, 0),
            Qt.Key_A: (-1, 0, 0),
            Qt.Key_S: (0, -1, 0),
            Qt.Key_D: (1, 0, 0),
            Qt.Key_Q: (0, 0, -1),
            Qt.Key_E: (0, 0, 1),
        }

        accel = 15.0
        for key in key_map:
            if(keys.get(key, False)):
                dirs = dirs + QtGui.QVector3D(*key_map[key])
        accel_vector = accel * dirs

        matrix = QtGui.QMatrix4x4()
        matrix.rotate(self.camera.orientation.y(), 0, 0, 1)

        drag = 15.0
        drag_vector = matrix.mapVector(-self.camera.velocity * drag)

        if accel_vector.x() == 0: accel_vector.setX(drag_vector.x())
        if accel_vector.y() == 0: accel_vector.setY(drag_vector.y())
        if accel_vector.z() == 0: accel_vector.setZ(drag_vector.z())

        matrix = QtGui.QMatrix4x4()
        matrix.rotate(-self.camera.orientation.y(), 0, 0, 1)

        self.camera.velocity += matrix.mapVector(accel_vector * delta_time)
        max_velocity = 7.0
        if self.camera.velocity.length() > max_velocity:
            self.camera.velocity.normalize()
            self.camera.velocity *= max_velocity
        self.camera.position += self.camera.velocity * delta_time

class Camera:
    def __init__(self):
        self.orientation = QtGui.QVector3D()
        self.position = QtGui.QVector3D(0, 0, .5)
        self.velocity = QtGui.QVector3D()
        self.vertical_fov = 50

    def view_transform(self):
        transform = QtGui.QMatrix4x4()
        transform.rotate(self.orientation.x(), 1, 0, 0)
        transform.rotate(self.orientation.y(), 0, 0, 1)
        transform.translate(-self.position)
        return transform

    def projection_transform(self, aspect_ratio):
        transform = QtGui.QMatrix4x4()
        transform.perspective(self.vertical_fov, aspect_ratio, .1, 100)
        return transform

class Light:
    def __init__(self):
        self.position = QtGui.QVector3D(8, 11, 8)
        self.look_at = QtGui.QVector3D(0, 0, 0)
        self.orientation = QtGui.QVector3D()
        self.velocity = QtGui.QVector3D()
        self.vertical_fov = 70
        self.need_shadow_render = True

    def view_transform(self):
        diff = self.look_at - self.position
        yaw = math.atan2(-diff.x(), diff.y())
        pitch = math.atan(diff.z() / math.sqrt(diff.x() * diff.x() + diff.y() * diff.y()))
        transform = QtGui.QMatrix4x4()
        transform.rotate(-math.degrees(pitch), 1, 0, 0)
        transform.rotate(-math.degrees(yaw), 0, 0, 1)
        transform.translate(-self.position)
        return transform

    def projection_transform(self):
        transform = QtGui.QMatrix4x4()
        transform.perspective(self.vertical_fov, 1, 3, 100)
        return transform

class Renderer(QtGui.QOpenGLFunctions):
    def __init__(self, gltf):
        super(Renderer, self).__init__()
        self.gltf = gltf
        self.camera = Camera()
        self.light = Light()

    def init_scene(self):
        self.initializeOpenGLFunctions()

        self.glEnable(GL.GL_DEPTH_TEST)
        self.glEnable(GL.GL_CULL_FACE)
        self.glClearColor(.2, .2, .2, 1)

        self.program = QtGui.QOpenGLShaderProgram()
        
        vertex_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Vertex)
        vertex_shader.compileSourceCode(vertex_source)
        self.program.addShader(vertex_shader)

        fragment_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Fragment)
        fragment_shader.compileSourceCode(fragment_source)
        self.program.addShader(fragment_shader)
        self.program.link()

        self.shadow_program = QtGui.QOpenGLShaderProgram()
        
        shadow_vertex_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Vertex)
        shadow_vertex_shader.compileSourceCode(shadow_vertex_source)
        self.shadow_program.addShader(shadow_vertex_shader)

        shadow_fragment_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Fragment)
        shadow_fragment_shader.compileSourceCode(shadow_fragment_source)
        self.shadow_program.addShader(shadow_fragment_shader)
        self.shadow_program.link()

        buffer = self.gltf.buffers[0]
        data = self.gltf.get_data_from_buffer_uri(buffer.uri)
        data = memoryview(data)
        self.buffers = []
        for view in self.gltf.bufferViews:
            buffer_types = {
                pygltflib.ARRAY_BUFFER : QtGui.QOpenGLBuffer.Type.VertexBuffer,
                pygltflib.ELEMENT_ARRAY_BUFFER : QtGui.QOpenGLBuffer.Type.IndexBuffer
            }
            buffer = QtGui.QOpenGLBuffer(buffer_types[view.target])
            buffer.create()
            buffer.bind()
            buffer.allocate(data[view.byteOffset:view.byteOffset + view.byteLength], view.byteLength)
            self.buffers.append(buffer)

        self.shadow_texture = GL.glGenTextures(1)
        self.glBindTexture(GL.GL_TEXTURE_2D, self.shadow_texture)
        self.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT, 1024, 1024, 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, VoidPtr(0))
        self.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        self.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        self.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        self.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        self.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_COMPARE_MODE, GL.GL_COMPARE_REF_TO_TEXTURE)
        self.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_COMPARE_FUNC, GL.GL_LEQUAL)

        self.shadow_fbo = GL.glGenFramebuffers(1)
        self.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.shadow_fbo)
        self.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_TEXTURE_2D, self.shadow_texture, 0)
        GL.glDrawBuffer(GL.GL_NONE)
        self.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    def draw_mesh(self, mesh, model_transform, program):
        self.program.setUniformValue('model_transform', model_transform)

        for primitive in mesh.primitives:
            material = self.gltf.materials[primitive.material]
            c = material.pbrMetallicRoughness.baseColorFactor
            color = QtGui.QColor()
            color.setRgbF(c[0], c[1], c[2], c[3])
            program.setUniformValue('color', color)

            accessor = self.gltf.accessors[primitive.attributes.POSITION]
            buffer = self.buffers[accessor.bufferView]
            buffer.bind()
            program.setAttributeBuffer('position', GL.GL_FLOAT, accessor.byteOffset, 3)
            buffer.release()
        
            accessor = self.gltf.accessors[primitive.attributes.NORMAL]
            buffer = self.buffers[accessor.bufferView]
            buffer.bind()
            program.setAttributeBuffer('normal', GL.GL_FLOAT, accessor.byteOffset, 3)
            buffer.release()
        
            accessor = self.gltf.accessors[primitive.indices]
            buffer = self.buffers[accessor.bufferView]
            buffer.bind()
            self.glDrawElements(GL.GL_TRIANGLES, accessor.count, GL.GL_UNSIGNED_INT, VoidPtr(int(accessor.byteOffset)))
            buffer.release()

    def draw_node(self, node, model_transform, program):
        if node.mesh:
            self.draw_mesh(self.gltf.meshes[node.mesh], model_transform, program)
        
        for n in node.children:
            child_node = self.gltf.nodes[n]
            matrix = model_transform
            if child_node.matrix:
                matrix = QtGui.QMatrix4x4(*child_node.matrix).transposed() * matrix
            
            self.draw_node(child_node, matrix, program)

    def render(self, width, height):
        if self.light.need_shadow_render:
            self.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.shadow_fbo)
            self.glViewport(0, 0, 1024, 1024)
            self.glClear(GL.GL_DEPTH_BUFFER_BIT)
            self.shadow_program.bind()

            projection_transform = self.light.projection_transform()
            projection_transform.rotate(-90, 1, 0, 0)
            view_transform = self.light.view_transform()
            
            self.shadow_program.setUniformValue('projection_transform', projection_transform)
            self.shadow_program.setUniformValue('view_transform', view_transform)

            model_transform = QtGui.QMatrix4x4()

            self.shadow_program.enableAttributeArray('position')
            self.shadow_program.enableAttributeArray('normal')
            
            scene = self.gltf.scenes[self.gltf.scene]
            for node in scene.nodes:
                self.draw_node(self.gltf.nodes[node], model_transform, self.shadow_program)

            self.shadow_program.disableAttributeArray('position')
            self.shadow_program.disableAttributeArray('normal')
            
            self.shadow_program.release()

            self.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
            self.need_shadow_render = False

        self.glClear(GL.GL_COLOR_BUFFER_BIT)
        self.glClear(GL.GL_DEPTH_BUFFER_BIT)
        self.glViewport(0, 0, width, height)
        self.program.bind()

        projection_transform = self.camera.projection_transform(float(width) / float(height))
        projection_transform.rotate(-90, 1, 0, 0)

        view_transform = self.camera.view_transform()
        
        self.program.setUniformValue('projection_transform', projection_transform)
        self.program.setUniformValue('view_transform', view_transform)
        self.program.setUniformValue('light_position', self.light.position)
        light_projection_transform = self.light.projection_transform()
        light_projection_transform.rotate(-90, 1, 0, 0)
        light_view_transform = self.light.view_transform()
        self.program.setUniformValue('light_transform', light_projection_transform * light_view_transform)
        self.program.setUniformValue('shadow_texture', 0)
        
        self.glActiveTexture(GL.GL_TEXTURE0)
        self.glBindTexture(GL.GL_TEXTURE_2D, self.shadow_texture)

        model_transform = QtGui.QMatrix4x4()

        self.program.enableAttributeArray('position')
        self.program.enableAttributeArray('normal')
        
        scene = self.gltf.scenes[self.gltf.scene]
        for node in scene.nodes:
            self.draw_node(self.gltf.nodes[node], model_transform, self.program)

        self.program.disableAttributeArray('position')
        self.program.disableAttributeArray('normal')
        
        self.program.release()

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