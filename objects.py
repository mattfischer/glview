from shaders import ShaderCache, Shader

from OpenGL import GL
import pygltflib

import glm
import math
import io
import ctypes
import numpy as np
from PIL import Image

class Camera:
    def __init__(self, position: glm.vec3, fov: float):
        self.orientation = glm.vec3()
        self.position = position
        self.velocity = glm.vec3()
        self.vertical_fov = fov

    def view_transform(self) -> glm.mat4:
        transform = glm.mat4()
        transform = transform * glm.rotate(math.radians(self.orientation.x), glm.vec3(1, 0, 0))
        transform = transform * glm.rotate(math.radians(self.orientation.y), glm.vec3(0, 1, 0))
        transform = transform * glm.translate(-self.position)
        return transform

    def projection_transform(self, aspect_ratio: float) -> glm.mat4:
        return glm.perspective(math.radians(self.vertical_fov), aspect_ratio, .1, 100)

class GltfObject:
    def __init__(self, filename: str):
        gltf = pygltflib.GLTF2().load(filename)
        self.gltf = gltf

    def init_gl(self, shader_cache: ShaderCache):
        self.program = shader_cache.get_shader('main')

        buffer = self.gltf.buffers[0]
        data = self.gltf.get_data_from_buffer_uri(buffer.uri)
        data = memoryview(data)
        self.buffers = []
        for view in self.gltf.bufferViews:
            buffer = GL.glGenBuffers(1)
            if view.target:
                GL.glBindBuffer(view.target, buffer)
                m = data[view.byteOffset:view.byteOffset + view.byteLength]
                GL.glBufferData(view.target, view.byteLength, np.array(m), GL.GL_STATIC_DRAW)
                GL.glBindBuffer(view.target, 0)
            self.buffers.append(buffer)

        self.textures = []
        for texture in self.gltf.textures:
            image = self.gltf.images[texture.source]
            sampler = self.gltf.samplers[texture.sampler]
            view = self.gltf.bufferViews[image.bufferView]
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
        for mesh in self.gltf.meshes:
            primitive_vaos = []
            for primitive in mesh.primitives:
                vao = GL.glGenVertexArrays(1)
                GL.glBindVertexArray(vao)

                GL.glEnableVertexAttribArray(0)
                GL.glEnableVertexAttribArray(1)
                GL.glEnableVertexAttribArray(2)

                accessor = self.gltf.accessors[primitive.attributes.POSITION]
                buffer = self.buffers[accessor.bufferView]
                GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer)
                GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(accessor.byteOffset))
            
                accessor = self.gltf.accessors[primitive.attributes.NORMAL]
                buffer = self.buffers[accessor.bufferView]
                GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer)
                GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(accessor.byteOffset))

                if primitive.attributes.TEXCOORD_0 is not None:
                    accessor = self.gltf.accessors[primitive.attributes.TEXCOORD_0]
                    buffer = self.buffers[accessor.bufferView]
                    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, buffer)
                    GL.glVertexAttribPointer(2, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(accessor.byteOffset))

                accessor = self.gltf.accessors[primitive.indices]
                buffer = self.buffers[accessor.bufferView]
                GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, buffer)
                
                primitive_vaos.append(vao)
            self.mesh_vaos.append(primitive_vaos)
        
    def draw_mesh(self, mesh: pygltflib.Mesh, model_transform: glm.mat4, program: Shader, primitive_vaos: list[GL.GLuint]):
        GL.glUniformMatrix4fv(program.uniform_location('model_transform'), 1, False, glm.value_ptr(model_transform))

        for (primitive, vao) in zip(mesh.primitives, primitive_vaos):
            material = self.gltf.materials[primitive.material]

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
                        GL.glUniform3fv(location, 1, color)
                        GL.glUniform1iv(program.uniform_location('has_color_texture'), 1, 0)

            GL.glBindVertexArray(vao)
            accessor = self.gltf.accessors[primitive.indices]
            GL.glDrawElements(GL.GL_TRIANGLES, accessor.count, GL.GL_UNSIGNED_INT, ctypes.c_void_p(accessor.byteOffset))

    def draw_node(self, node: pygltflib.Node, model_transform: glm.mat4, program: Shader):
        if node.matrix:
            model_transform = model_transform * glm.mat4(*node.matrix)

        if node.mesh is not None:
            self.draw_mesh(self.gltf.meshes[node.mesh], model_transform, program, self.mesh_vaos[node.mesh])
        
        for n in node.children:
            child_node = self.gltf.nodes[n]
            
            self.draw_node(child_node, model_transform, program)

    def render(self, program: Shader):
        model_transform = glm.mat4()
        scene = self.gltf.scenes[self.gltf.scene]
        for node in scene.nodes:
            self.draw_node(self.gltf.nodes[node], model_transform, program)

class Skybox:
    def __init__(self, filename):
        self.filename = filename

    def init_gl(self, shader_cache: ShaderCache):
        self.program = shader_cache.get_shader('skybox')

        self.vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.vao)

        GL.glEnableVertexAttribArray(0)
                
        self.vertex_buffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vertex_buffer)
        vertex_data = np.array([-1.0, -1.0, -1.0,  1.0, -1.0, -1.0,
                                -1.0,  1.0, -1.0,  1.0,  1.0, -1.0,
                                -1.0, -1.0,  1.0,  1.0, -1.0,  1.0,
                                -1.0,  1.0,  1.0,  1.0,  1.0,  1.0], np.float32)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, vertex_data, GL.GL_STATIC_DRAW)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, ctypes.c_void_p(0))

        self.index_buffer = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, self.index_buffer)
        index_data = np.array([2, 3, 6,  3, 7, 6,  0, 4, 5,  0, 5, 1,
                               0, 2, 6,  0, 6, 4,  1, 5, 7,  1, 7, 3,
                               0, 1, 2,  2, 1, 3,  4, 6, 7,  4, 7, 5], np.uint32)

        GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, index_data, GL.GL_STATIC_DRAW)
        GL.glBindVertexArray(0)

        pil_image = Image.open(self.filename)
        self.texture = GL.glGenTextures(1)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.texture)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_CUBE_MAP, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        
        face_size = pil_image.width / 4

        face_map = {
            GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X: (face_size * 2, face_size),
            GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X: (0, face_size),
            GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y: (face_size, 0),
            GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y: (face_size, face_size * 2),
            GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z: (face_size, face_size),
            GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z: (face_size * 3, face_size)
        }

        for face in face_map:
            (x, y) = face_map[face]
            face_image = pil_image.crop((x, y, x + face_size, y + face_size))
            GL.glTexImage2D(face, 0, GL.GL_RGB, face_size, face_size, 0, GL.GL_RGB, GL.GL_UNSIGNED_BYTE, face_image.tobytes())
        GL.glGenerateMipmap(GL.GL_TEXTURE_CUBE_MAP)
        GL.glEnable(GL.GL_TEXTURE_CUBE_MAP_SEAMLESS)

    def render(self):
        GL.glDepthFunc(GL.GL_LEQUAL)
        GL.glBindVertexArray(self.vao)

        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.texture)
        GL.glUniform1iv(self.program.uniform_location('skybox_texture'), 1, 0)
    
        GL.glDrawElements(GL.GL_TRIANGLES, 12 * 3, GL.GL_UNSIGNED_INT, ctypes.c_void_p(0))
        GL.glBindVertexArray(0)
        GL.glDepthFunc(GL.GL_LESS)