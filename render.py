from OpenGL import GL
import pygltflib

from objects import GltfObject, Light, Scene
import numpy as np
import ctypes
import glm
import math
from PIL import Image
import io
import sys

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

class ShaderCache:
    def __init__(self):
        self.cache = {}

    def get_shader(self, name: str) -> Shader:
        if name not in self.cache:
            program = GL.glCreateProgram()
            with open('shaders/%s.vert' % name) as file:
                shader = GL.glCreateShader(GL.GL_VERTEX_SHADER)
                source = file.read()
                GL.glShaderSource(shader, [source])
                GL.glCompileShader(shader)
                if GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS) == GL.GL_FALSE:
                    log = GL.glGetShaderInfoLog(shader)
                    print(log)
                    sys.exit(1)
                GL.glAttachShader(program, shader)

            with open('shaders/%s.frag' % name) as file:
                shader = GL.glCreateShader(GL.GL_FRAGMENT_SHADER)
                source = file.read()
                GL.glShaderSource(shader, [source])
                GL.glCompileShader(shader)
                if GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS) == GL.GL_FALSE:
                    log = GL.glGetShaderInfoLog(shader)
                    print(log)
                    sys.exit(1)
                GL.glAttachShader(program, shader)

            GL.glLinkProgram(program)
            if GL.glGetProgramiv(program, GL.GL_LINK_STATUS) == GL.GL_FALSE:
                log = GL.glGetProgramInfoLog(program)
                print(log)
                sys.exit(1)
            
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
            if view.target:
                GL.glBindBuffer(view.target, buffer)
                m = data[view.byteOffset:view.byteOffset + view.byteLength]
                GL.glBufferData(view.target, view.byteLength, np.array(m), GL.GL_STATIC_DRAW)
                GL.glBindBuffer(view.target, 0)
            self.buffers.append(buffer)

        self.textures = []
        for texture in self.gltf_object.gltf.textures:
            image = self.gltf_object.gltf.images[texture.source]
            sampler = self.gltf_object.gltf.samplers[texture.sampler]
            view = self.gltf_object.gltf.bufferViews[image.bufferView]
            imagedata = data[view.byteOffset:view.byteOffset + view.byteLength]
            file = io.BytesIO(imagedata)
            pil_image = Image.open(file).convert('RGB')
            tex = GL.glGenTextures(1)
            GL.glActiveTexture(GL.GL_TEXTURE0)
            GL.glBindTexture(GL.GL_TEXTURE_2D, tex)
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB, pil_image.width, pil_image.height, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, pil_image.tobytes())
            GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, sampler.minFilter)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, sampler.magFilter)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, sampler.wrapS)
            GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, sampler.wrapT)
            self.textures.append(tex)

        self.mesh_vaos = []
        for mesh in self.gltf_object.gltf.meshes:
            primitive_vaos = []
            for primitive in mesh.primitives:
                vao = GL.glGenVertexArrays(1)
                GL.glBindVertexArray(vao)

                GL.glEnableVertexAttribArray(0)
                GL.glEnableVertexAttribArray(1)
                GL.glEnableVertexAttribArray(2)

                accessor = self.gltf_object.gltf.accessors[primitive.attributes.POSITION]
                buffer = self.buffers[accessor.bufferView]
                GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer)
                GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(accessor.byteOffset))
            
                accessor = self.gltf_object.gltf.accessors[primitive.attributes.NORMAL]
                buffer = self.buffers[accessor.bufferView]
                GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer)
                GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(accessor.byteOffset))

                if primitive.attributes.TEXCOORD_0 is not None:
                    accessor = self.gltf_object.gltf.accessors[primitive.attributes.TEXCOORD_0]
                    buffer = self.buffers[accessor.bufferView]
                    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer)
                    GL.glVertexAttribPointer(2, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(accessor.byteOffset))

                accessor = self.gltf_object.gltf.accessors[primitive.indices]
                buffer = self.buffers[accessor.bufferView]
                GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, buffer)
                
                primitive_vaos.append(vao)
            self.mesh_vaos.append(primitive_vaos)
        
    def draw_mesh(self, mesh: pygltflib.Mesh, model_transform: glm.mat4, program: Shader, primitive_vaos):
        GL.glUniformMatrix4fv(program.uniform_location('model_transform'), 1, False, glm.value_ptr(model_transform))

        for (primitive, vao) in zip(mesh.primitives, primitive_vaos):
            material = self.gltf_object.gltf.materials[primitive.material]

            if material.pbrMetallicRoughness:
                baseColorTexture = material.pbrMetallicRoughness.baseColorTexture
                if baseColorTexture:
                    location = program.uniform_location('color_texture')
                    if location != -1:
                        tex = baseColorTexture.index
                        GL.glActiveTexture(GL.GL_TEXTURE1)
                        GL.glBindTexture(GL.GL_TEXTURE_2D, self.textures[tex])
                        GL.glUniform1iv(location, 1, 1)
                        GL.glUniform1iv(program.uniform_location('has_color_texture'), 1, 1)
                else:
                    location = program.uniform_location('base_color')
                    if location != -1:
                        color = material.pbrMetallicRoughness.baseColorFactor
                        GL.glUniform4fv(location, 1, color)
                        GL.glUniform1iv(program.uniform_location('has_color_texture'), 1, 0)

            GL.glBindVertexArray(vao)
            accessor = self.gltf_object.gltf.accessors[primitive.indices]
            GL.glDrawElements(GL.GL_TRIANGLES, accessor.count, GL.GL_UNSIGNED_INT, ctypes.c_void_p(accessor.byteOffset))

    def draw_node(self, node: pygltflib.Node, model_transform: glm.mat4, program: Shader):
        if node.matrix:
            model_transform = model_transform * glm.mat4(*node.matrix)

        if node.mesh is not None:
            self.draw_mesh(self.gltf_object.gltf.meshes[node.mesh], model_transform, program, self.mesh_vaos[node.mesh])
        
        for n in node.children:
            child_node = self.gltf_object.gltf.nodes[n]
            
            self.draw_node(child_node, model_transform, program)

    def render(self, program: Shader):
        model_transform = glm.rotate(math.radians(90), glm.vec3(1, 0, 0))
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
        GL.glViewport(0, 0, 1024, 1024)

        for face in CUBE_FACES:
            GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_DEPTH_ATTACHMENT, face, self.shadow_texture, 0)
        
            GL.glClear(GL.GL_DEPTH_BUFFER_BIT)

            projection_transform = glm.perspective(math.radians(90), 1, .1, 30)

            view_transform = glm.mat4()
            view_transform = view_transform * glm.scale(glm.vec3(1, -1, -1))
            face_transforms = {
                GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X: (math.radians(-90), glm.vec3(0, 1, 0)),
                GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X: (math.radians(90), glm.vec3(0, 1, 0)),
                GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y: (math.radians(90), glm.vec3(1, 0, 0)),
                GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y: (math.radians(-90), glm.vec3(1, 0, 0)),
                GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z: (math.radians(0), glm.vec3(0, 1, 0)),
                GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z: (math.radians(180), glm.vec3(0, 1, 0))
            }
            view_transform = view_transform * glm.rotate(*face_transforms[face])
            view_transform = view_transform * glm.translate(-self.light.position)
            
            GL.glUniformMatrix4fv(self.shadow_program.uniform_location('projection_transform'), 1, False, glm.value_ptr(projection_transform))
            GL.glUniformMatrix4fv(self.shadow_program.uniform_location('view_transform'), 1, False, glm.value_ptr(view_transform))

            for obj in scene.objects:
                obj.renderer.render(self.shadow_program)
        
        GL.glUseProgram(0)

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

            projection_transform = self.scene.camera.projection_transform(float(width) / float(height))
            projection_transform = projection_transform * glm.rotate(math.radians(-90), glm.vec3(1, 0, 0))
            view_transform = self.scene.camera.view_transform()
            
            GL.glUniformMatrix4fv(program.uniform_location('projection_transform'), 1, GL.GL_FALSE, glm.value_ptr(projection_transform))
            GL.glUniformMatrix4fv(program.uniform_location('view_transform'), 1, GL.GL_FALSE, glm.value_ptr(view_transform))
            GL.glUniform3fv(program.uniform_location('light_position'), 1, glm.value_ptr(self.scene.light.position))
            GL.glUniform1i(program.uniform_location('shadow_texture'), 0)

            GL.glActiveTexture(GL.GL_TEXTURE0)
            GL.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.scene.light.renderer.shadow_texture)

            obj.renderer.render(program)
            
            GL.glUseProgram(0)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, default_fbo)
        GL.glViewport(0, 0, width, height)
        
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glUseProgram(self.postproc_program.program)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.render_color_texture)
        GL.glUniform1i(self.postproc_program.uniform_location('frame'), 0)

        GL.glDrawArrays(GL.GL_TRIANGLE_FAN, 0, 4)
        GL.glUseProgram(0)
        GL.glEnable(GL.GL_DEPTH_TEST)
