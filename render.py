from PySide2 import QtCore, QtWidgets, QtGui
from PySide2.QtCore import Slot
from PySide2.QtCore import Qt
from PySide2.support import VoidPtr

from OpenGL import GL
import numpy as np
import pygltflib

CUBE_FACES = [
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X,
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y,
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z,
]

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
        self.need_shadow_render = True

    def view_transform(self, face):
        transform = QtGui.QMatrix4x4()
        transform.scale(1, -1, -1)
        if face == GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X:
            transform.rotate(-90, 0, 1, 0)
        elif face == GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X:
            transform.rotate(90, 0, 1, 0)
        elif face == GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y:
            transform.rotate(90, 1, 0, 0)
        elif face == GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y:
            transform.rotate(-90, 1, 0, 0)
        elif face == GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z:
            transform.rotate(180, 0, 1, 0)
        elif face == GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z:
            transform.rotate(180, 0, 1, 0)

        transform.translate(-self.position)
        return transform

    def projection_transform(self):
        transform = QtGui.QMatrix4x4()
        transform.perspective(90, 1, .1, 30)
        return transform

class MeshRenderer:
    def __init__(self, gltf):
        self.gltf = gltf

    def init_gl(self, gl):
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

    def draw_mesh(self, mesh, gl, model_transform, program):
        program.setUniformValue('model_transform', model_transform)

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
            gl.glDrawElements(GL.GL_TRIANGLES, accessor.count, GL.GL_UNSIGNED_INT, VoidPtr(int(accessor.byteOffset)))
            buffer.release()

    def draw_node(self, node, gl, model_transform, program):
        if node.mesh:
            self.draw_mesh(self.gltf.meshes[node.mesh], gl, model_transform, program)
        
        for n in node.children:
            child_node = self.gltf.nodes[n]
            matrix = model_transform
            if child_node.matrix:
                matrix = QtGui.QMatrix4x4(*child_node.matrix).transposed() * matrix
            
            self.draw_node(child_node, gl, matrix, program)

    def render(self, gl, program):
        model_transform = QtGui.QMatrix4x4()
        scene = self.gltf.scenes[self.gltf.scene]
        for node in scene.nodes:
            self.draw_node(self.gltf.nodes[node], gl, model_transform, program)

class ShadowRenderer:
    def __init__(self, light):
        self.light = light

    def init_gl(self, gl):
        self.shadow_texture = GL.glGenTextures(1)
        gl.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.shadow_texture)
        gl.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        gl.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        gl.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_COMPARE_MODE, GL.GL_COMPARE_REF_TO_TEXTURE)
        gl.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_COMPARE_FUNC, GL.GL_LEQUAL)

        for face in CUBE_FACES:
            gl.glTexImage2D(face, 0, GL.GL_DEPTH_COMPONENT, 1024, 1024, 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, VoidPtr(0))

        self.shadow_fbo = GL.glGenFramebuffers(1)
        gl.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.shadow_fbo)
        GL.glDrawBuffer(GL.GL_NONE)
        gl.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    def render(self, gl, mesh_renderer, shadow_program):
        if not self.light.need_shadow_render:
            return

        gl.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.shadow_fbo)
        shadow_program.bind()
        gl.glViewport(0, 0, 1024, 1024)

        for face in CUBE_FACES:
            gl.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, face, self.shadow_texture, 0)
        
            gl.glClear(GL.GL_DEPTH_BUFFER_BIT)

            projection_transform = self.light.projection_transform()
            view_transform = self.light.view_transform(face)
            
            shadow_program.setUniformValue('projection_transform', projection_transform)
            shadow_program.setUniformValue('view_transform', view_transform)

            mesh_renderer.render(gl, shadow_program)
        
        shadow_program.release()

        gl.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        self.light.need_shadow_render = False

class Renderer(QtGui.QOpenGLFunctions):
    def __init__(self, gltf):
        super(Renderer, self).__init__()
        self.camera = Camera()
        self.light = Light()
        self.mesh_renderer = MeshRenderer(gltf)
        self.shadow_renderer = ShadowRenderer(self.light)

    def init_scene(self):
        self.initializeOpenGLFunctions()

        self.glEnable(GL.GL_DEPTH_TEST)
        self.glEnable(GL.GL_CULL_FACE)
        self.glClearColor(.2, .2, .2, 1)

        self.program = QtGui.QOpenGLShaderProgram()
        
        vertex_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Vertex)
        vertex_shader.compileSourceFile('shaders/main.vert')
        self.program.addShader(vertex_shader)

        fragment_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Fragment)
        fragment_shader.compileSourceFile('shaders/main.frag')
        self.program.addShader(fragment_shader)
        self.program.link()
        self.program.enableAttributeArray('position')
        self.program.enableAttributeArray('normal')

        self.shadow_program = QtGui.QOpenGLShaderProgram()
        
        shadow_vertex_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Vertex)
        shadow_vertex_shader.compileSourceFile('shaders/shadow.vert')
        self.shadow_program.addShader(shadow_vertex_shader)

        shadow_fragment_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Fragment)
        shadow_fragment_shader.compileSourceFile('shaders/shadow.frag')
        self.shadow_program.addShader(shadow_fragment_shader)
        self.shadow_program.link()
        self.shadow_program.enableAttributeArray('position')
        self.shadow_program.enableAttributeArray('normal')

        self.mesh_renderer.init_gl(self)
        self.shadow_renderer.init_gl(self)

    def render(self, width, height):
        self.shadow_renderer.render(self, self.mesh_renderer, self.shadow_program)

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
        self.program.setUniformValue('shadow_texture', 0)
        
        self.glActiveTexture(GL.GL_TEXTURE0)
        self.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.shadow_renderer.shadow_texture)

        self.mesh_renderer.render(self, self.program)
        
        self.program.release()
