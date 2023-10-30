from PySide2 import QtGui
from PySide2.support import VoidPtr

from OpenGL import GL
import pygltflib

from objects import GltfObject, Light, Scene
import numpy as np
import ctypes

CUBE_FACES = [
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X,
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y,
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z,
]

class Shader:
    def __init__(self, program):
        self.program = program
        self.uniforms = {}
        self.attributes = {}

    def uniform_location(self, name):
        if name not in self.uniforms:
            self.uniforms[name] = GL.glGetUniformLocation(self.program, name)
        return self.uniforms[name]

    def attribute_location(self, name):
        if name not in self.attributes:
            self.attributes[name] = GL.glGetAttribLocation(self.program, name)
        return self.attributes[name]

class ShaderCache:
    def __init__(self):
        self.cache = {}

    def get_shader(self, name: str) -> GL.GLuint:
        if name not in self.cache:
            program = GL.glCreateProgram()
            with open('shaders/%s.vert' % name) as file:
                shader = GL.glCreateShader(GL.GL_VERTEX_SHADER)
                source = file.read()
                GL.glShaderSource(shader, [source])
                GL.glCompileShader(shader)
                GL.glAttachShader(program, shader)

            with open('shaders/%s.frag' % name) as file:
                shader = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
                source = file.read()
                GL.glShaderSource(shader, [source])
                GL.glCompileShader(shader)
                GL.glAttachShader(program, shader)

            GL.glLinkProgram(program)
            self.cache[name] = Shader(program)

        return self.cache[name]

class GltfRenderer:
    def __init__(self, gltf_object: GltfObject):
        self.gltf_object = gltf_object

    def init_gl(self, shader_cache: ShaderCache):
        self.program = shader_cache.get_shader('main')

        buffer = self.gltf_object.gltf.buffers[0]
        data = self.gltf_object.gltf.get_data_from_buffer_uri(buffer.uri)
        data = memoryview(data)
        self.buffers = []
        for view in self.gltf_object.gltf.bufferViews:
            buffer = GL.glGenBuffers(1)
            buffer_types = {
                pygltflib.ARRAY_BUFFER : GL.GL_ARRAY_BUFFER,
                pygltflib.ELEMENT_ARRAY_BUFFER : GL.GL_ELEMENT_ARRAY_BUFFER
            }
            target = buffer_types[view.target]
            GL.glBindBuffer(target, buffer)
            m = data[view.byteOffset:view.byteOffset + view.byteLength]
            GL.glBufferData(target, view.byteLength, np.array(m), GL.GL_STATIC_DRAW)
            GL.glBindBuffer(target, 0)
            self.buffers.append(buffer)

    def draw_mesh(self, mesh: pygltflib.Mesh, model_transform: QtGui.QMatrix4x4, program: Shader):
        GL.glUniformMatrix4fv(program.uniform_location('model_transform'), 1, False, model_transform.data())

        for primitive in mesh.primitives:
            material = self.gltf_object.gltf.materials[primitive.material]
            c = material.pbrMetallicRoughness.baseColorFactor
            GL.glUniform4f(program.uniform_location('color'), c[0], c[1], c[2], c[3])

            accessor = self.gltf_object.gltf.accessors[primitive.attributes.POSITION]
            buffer = self.buffers[accessor.bufferView]
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer)
            GL.glVertexAttribPointer(program.attribute_location('position'), 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(accessor.byteOffset))
        
            accessor = self.gltf_object.gltf.accessors[primitive.attributes.NORMAL]
            buffer = self.buffers[accessor.bufferView]
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer)
            l = program.attribute_location('normal')
            if l != -1:
                GL.glVertexAttribPointer(l, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(accessor.byteOffset))
        
            accessor = self.gltf_object.gltf.accessors[primitive.indices]
            buffer = self.buffers[accessor.bufferView]
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, buffer)
            GL.glDrawElements(GL.GL_TRIANGLES, accessor.count, GL.GL_UNSIGNED_INT, ctypes.c_void_p(accessor.byteOffset))

    def draw_node(self, node: pygltflib.Node, model_transform: QtGui.QMatrix4x4, program: Shader):
        if node.mesh:
            self.draw_mesh(self.gltf_object.gltf.meshes[node.mesh], model_transform, program)
        
        for n in node.children:
            child_node = self.gltf_object.gltf.nodes[n]
            matrix = model_transform
            if child_node.matrix:
                matrix = QtGui.QMatrix4x4(*child_node.matrix).transposed() * matrix
            
            self.draw_node(child_node, matrix, program)

    def render(self, program: Shader):
        model_transform = QtGui.QMatrix4x4()
        scene = self.gltf_object.gltf.scenes[self.gltf_object.gltf.scene]
        for node in scene.nodes:
            self.draw_node(self.gltf_object.gltf.nodes[node], model_transform, program)

class ShadowRenderer:
    def __init__(self, light: Light):
        self.light = light

    def init_gl(self, shader_cache: ShaderCache):
        self.shadow_program = shader_cache.get_shader('shadow')

        self.shadow_texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.shadow_texture)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_COMPARE_MODE, GL.GL_COMPARE_REF_TO_TEXTURE)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_COMPARE_FUNC, GL.GL_LEQUAL)

        for face in CUBE_FACES:
            GL.glTexImage2D(face, 0, GL.GL_DEPTH_COMPONENT, 1024, 1024, 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)

        self.shadow_fbo = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.shadow_fbo)
        GL.glDrawBuffer(GL.GL_NONE)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)

    def render(self, scene: Scene):
        if not self.light.need_shadow_render:
            return

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.shadow_fbo)
        GL.glUseProgram(self.shadow_program.program)
        GL.glEnableVertexAttribArray(self.shadow_program.attribute_location('position'))
        GL.glViewport(0, 0, 1024, 1024)

        for face in CUBE_FACES:
            GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, face, self.shadow_texture, 0)
        
            GL.glClear(GL.GL_DEPTH_BUFFER_BIT)

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
            
            GL.glUniformMatrix4fv(self.shadow_program.uniform_location('projection_transform'), 1, False, projection_transform.data())
            GL.glUniformMatrix4fv(self.shadow_program.uniform_location('view_transform'), 1, False, view_transform.data())

            for obj in scene.objects:
                obj.renderer.render(self.shadow_program)
        
        GL.glUseProgram(0)
        GL.glDisableVertexAttribArray(self.shadow_program.attribute_location('position'))

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)
        self.light.need_shadow_render = False

class Renderer:
    def __init__(self, scene: Scene):
        self.scene = scene
        for obj in self.scene.objects:
            obj.renderer = GltfRenderer(obj)
        self.scene.light.renderer = ShadowRenderer(self.scene.light)
        self.shader_cache = ShaderCache()

    def init_gl(self, width: int, height: int):
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glClearColor(.2, .2, .2, 1)

        for obj in self.scene.objects:
            obj.renderer.init_gl(self.shader_cache)
        self.scene.light.renderer.init_gl(self.shader_cache)

        self.render_color_texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.render_color_texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, width, height, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, None)

        self.render_depth_texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.render_depth_texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_DEPTH_COMPONENT, width, height, 0, GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT, None)

        default_fbo = GL.glGetIntegerv(GL.GL_DRAW_FRAMEBUFFER_BINDING)

        self.render_fbo = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.render_fbo)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self.render_color_texture, 0)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, GL.GL_TEXTURE_2D, self.render_depth_texture, 0)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, default_fbo)

        self.postproc_program = self.shader_cache.get_shader('postproc')

    def render(self, width: int, height: int):
        default_fbo = GL.glGetIntegerv(GL.GL_DRAW_FRAMEBUFFER_BINDING)

        self.scene.light.renderer.render(self.scene)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.render_fbo)
        
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
        GL.glViewport(0, 0, width, height)

        for obj in self.scene.objects:
            program = obj.renderer.program
            GL.glUseProgram(program.program)
            GL.glEnableVertexAttribArray(program.attribute_location('position'))
            GL.glEnableVertexAttribArray(program.attribute_location('normal'))

            projection_transform = self.scene.camera.projection_transform(float(width) / float(height))
            projection_transform.rotate(-90, 1, 0, 0)

            view_transform = self.scene.camera.view_transform()
            
            GL.glUniformMatrix4fv(program.uniform_location('projection_transform'), 1, GL.GL_FALSE, projection_transform.data())
            GL.glUniformMatrix4fv(program.uniform_location('view_transform'), 1, GL.GL_FALSE, view_transform.data())
            GL.glUniform3f(program.uniform_location('light_position'), self.scene.light.position.x(), self.scene.light.position.y(), self.scene.light.position.z())
            GL.glUniform1i(program.uniform_location('shadow_texture'), 0)

            GL.glActiveTexture(GL.GL_TEXTURE0)
            GL.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.scene.light.renderer.shadow_texture)

            obj.renderer.render(program)
            
            GL.glUseProgram(0)
            GL.glDisableVertexAttribArray(program.attribute_location('position'))
            GL.glDisableVertexAttribArray(program.attribute_location('normal'))

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, default_fbo)
        GL.glViewport(0, 0, width, height)
        
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glUseProgram(self.postproc_program.program)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.render_color_texture)
        GL.glUniform1i(self.postproc_program.uniform_location('frame'), 0)

        GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, 4)
        GL.glUseProgram(0)
        GL.glEnable(GL.GL_DEPTH_TEST)
