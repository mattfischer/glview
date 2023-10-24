from PySide2 import QtGui
from PySide2.support import VoidPtr

from OpenGL import GL
import pygltflib

from objects import GltfObject, Light, Scene

CUBE_FACES = [
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X,
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y,
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z,
]

class ShaderCache:
    def __init__(self):
        self.cache = {}

    def get_shader(self, name: str) -> QtGui.QOpenGLShaderProgram:
        if name not in self.cache:
            program = QtGui.QOpenGLShaderProgram()
        
            vertex_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Vertex)
            vertex_shader.compileSourceFile('shaders/%s.vert' % name)
            program.addShader(vertex_shader)

            fragment_shader = QtGui.QOpenGLShader(QtGui.QOpenGLShader.Fragment)
            fragment_shader.compileSourceFile('shaders/%s.frag' % name)
            program.addShader(fragment_shader)
            program.link()
            self.cache[name] = program

        return self.cache[name]

class GltfRenderer:
    def __init__(self, gltf_object: GltfObject):
        self.gltf_object = gltf_object

    def init_gl(self, gl: QtGui.QOpenGLFunctions, shader_cache: ShaderCache):
        self.program = shader_cache.get_shader('main')
        self.program.enableAttributeArray('position')
        self.program.enableAttributeArray('normal')

        buffer = self.gltf_object.gltf.buffers[0]
        data = self.gltf_object.gltf.get_data_from_buffer_uri(buffer.uri)
        data = memoryview(data)
        self.buffers = []
        for view in self.gltf_object.gltf.bufferViews:
            buffer_types = {
                pygltflib.ARRAY_BUFFER : QtGui.QOpenGLBuffer.Type.VertexBuffer,
                pygltflib.ELEMENT_ARRAY_BUFFER : QtGui.QOpenGLBuffer.Type.IndexBuffer
            }
            buffer = QtGui.QOpenGLBuffer(buffer_types[view.target])
            buffer.create()
            buffer.bind()
            buffer.allocate(data[view.byteOffset:view.byteOffset + view.byteLength], view.byteLength)
            self.buffers.append(buffer)

    def draw_mesh(self, mesh: pygltflib.Mesh, gl: QtGui.QOpenGLFunctions, model_transform: QtGui.QMatrix4x4, program: QtGui.QOpenGLShaderProgram):
        program.setUniformValue('model_transform', model_transform)

        for primitive in mesh.primitives:
            material = self.gltf_object.gltf.materials[primitive.material]
            c = material.pbrMetallicRoughness.baseColorFactor
            color = QtGui.QColor()
            color.setRgbF(c[0], c[1], c[2], c[3])
            program.setUniformValue('color', color)

            accessor = self.gltf_object.gltf.accessors[primitive.attributes.POSITION]
            buffer = self.buffers[accessor.bufferView]
            buffer.bind()
            program.setAttributeBuffer('position', GL.GL_FLOAT, accessor.byteOffset, 3)
            buffer.release()
        
            accessor = self.gltf_object.gltf.accessors[primitive.attributes.NORMAL]
            buffer = self.buffers[accessor.bufferView]
            buffer.bind()
            program.setAttributeBuffer('normal', GL.GL_FLOAT, accessor.byteOffset, 3)
            buffer.release()
        
            accessor = self.gltf_object.gltf.accessors[primitive.indices]
            buffer = self.buffers[accessor.bufferView]
            buffer.bind()
            gl.glDrawElements(GL.GL_TRIANGLES, accessor.count, GL.GL_UNSIGNED_INT, VoidPtr(int(accessor.byteOffset)))
            buffer.release()

    def draw_node(self, node: pygltflib.Node, gl: QtGui.QOpenGLFunctions, model_transform: QtGui.QMatrix4x4, program: QtGui.QOpenGLShaderProgram):
        if node.mesh:
            self.draw_mesh(self.gltf_object.gltf.meshes[node.mesh], gl, model_transform, program)
        
        for n in node.children:
            child_node = self.gltf_object.gltf.nodes[n]
            matrix = model_transform
            if child_node.matrix:
                matrix = QtGui.QMatrix4x4(*child_node.matrix).transposed() * matrix
            
            self.draw_node(child_node, gl, matrix, program)

    def render(self, gl: QtGui.QOpenGLFunctions, program: QtGui.QOpenGLShaderProgram):
        model_transform = QtGui.QMatrix4x4()
        scene = self.gltf_object.gltf.scenes[self.gltf_object.gltf.scene]
        for node in scene.nodes:
            self.draw_node(self.gltf_object.gltf.nodes[node], gl, model_transform, program)

class ShadowRenderer:
    def __init__(self, light: Light):
        self.light = light

    def init_gl(self, gl: QtGui.QOpenGLFunctions, shader_cache: ShaderCache):
        self.shadow_program = shader_cache.get_shader('shadow')
        self.shadow_program.enableAttributeArray('position')
        self.shadow_program.enableAttributeArray('normal')

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

    def render(self, gl: QtGui.QOpenGLFunctions, scene: Scene):
        if not self.light.need_shadow_render:
            return

        gl.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.shadow_fbo)
        self.shadow_program.bind()
        gl.glViewport(0, 0, 1024, 1024)

        for face in CUBE_FACES:
            gl.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, face, self.shadow_texture, 0)
        
            gl.glClear(GL.GL_DEPTH_BUFFER_BIT)

            projection_transform = QtGui.QMatrix4x4()
            projection_transform.perspective(90, 1, .1, 30)

            view_transform = QtGui.QMatrix4x4()
            view_transform.scale(1, -1, -1)
            face_transforms = {
                GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X: (-90, 0, 1, 0),
                GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X: (90, 0, 1, 0),
                GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y: (90, 1, 0, 0),
                GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y: (-90, 1, 0, 0),
                GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z: (0, 0, 1, 0),
                GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z: (180, 0, 1, 0)
            }
            view_transform.rotate(*face_transforms[face])
            view_transform.translate(-self.light.position)
            
            self.shadow_program.setUniformValue('projection_transform', projection_transform)
            self.shadow_program.setUniformValue('view_transform', view_transform)

            for obj in scene.objects:
                obj.renderer.render(gl, self.shadow_program)
        
        self.shadow_program.release()

        gl.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        self.light.need_shadow_render = False

class Renderer:
    def __init__(self, scene: Scene):
        self.scene = scene
        for obj in self.scene.objects:
            obj.renderer = GltfRenderer(obj)
        self.scene.light.renderer = ShadowRenderer(self.scene.light)
        self.shader_cache = ShaderCache()

    def init_gl(self, gl: QtGui.QOpenGLFunctions, width: int, height: int):
        gl.glEnable(GL.GL_DEPTH_TEST)
        gl.glEnable(GL.GL_CULL_FACE)
        gl.glClearColor(.2, .2, .2, 1)

        for obj in self.scene.objects:
            obj.renderer.init_gl(gl, self.shader_cache)
        self.scene.light.renderer.init_gl(gl, self.shader_cache)

        self.render_color_texture = GL.glGenTextures(1)
        gl.glBindTexture(GL.GL_TEXTURE_2D, self.render_color_texture)
        gl.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        gl.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        gl.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        gl.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, width, height, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, VoidPtr(0))

        self.render_depth_texture = GL.glGenTextures(1)
        gl.glBindTexture(GL.GL_TEXTURE_2D, self.render_depth_texture)
        gl.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        gl.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        gl.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        gl.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT, width, height, 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, VoidPtr(0))

        self.render_fbo = GL.glGenFramebuffers(1)
        gl.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.render_fbo)
        gl.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self.render_color_texture, 0)
        gl.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_TEXTURE_2D, self.render_depth_texture, 0)
        gl.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

        self.postproc_program = self.shader_cache.get_shader('postproc')

    def render(self, gl: QtGui.QOpenGLFunctions, width: int, height: int):
        self.scene.light.renderer.render(gl, self.scene)

        gl.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.render_fbo)
        
        gl.glClear(GL.GL_COLOR_BUFFER_BIT)
        gl.glClear(GL.GL_DEPTH_BUFFER_BIT)
        gl.glViewport(0, 0, width, height)

        for obj in self.scene.objects:
            program = obj.renderer.program
            program.bind()

            projection_transform = self.scene.camera.projection_transform(float(width) / float(height))
            projection_transform.rotate(-90, 1, 0, 0)

            view_transform = self.scene.camera.view_transform()
            
            program.setUniformValue('projection_transform', projection_transform)
            program.setUniformValue('view_transform', view_transform)
            program.setUniformValue('light_position', self.scene.light.position)
            program.setUniformValue('shadow_texture', 0)
            
            gl.glActiveTexture(GL.GL_TEXTURE0)
            gl.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.scene.light.renderer.shadow_texture)

            obj.renderer.render(gl, program)
            
            program.release()
        
        gl.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        gl.glViewport(0, 0, width, height)
        
        gl.glDisable(GL.GL_DEPTH_TEST)
        self.postproc_program.bind()
        gl.glBindTexture(GL.GL_TEXTURE_2D, self.render_color_texture)
        self.postproc_program.setUniformValue('frame', 0)

        gl.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, 4)
        self.postproc_program.release()
        gl.glEnable(GL.GL_DEPTH_TEST)
