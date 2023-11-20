from OpenGL import GL

from objects import GltfObject, Camera
from lights import Light
from shaders import ShaderCache

import glm
import math

class Scene:
    def __init__(self, objects: list[GltfObject], camera: Camera, light: Light):
        self.objects = objects
        self.camera = camera
        self.light = light
        self.shader_cache = ShaderCache()

    def init_gl(self, width: int, height: int):
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_CULL_FACE)
        GL.glClearColor(.1, .1, .1, 1)

        for obj in self.objects:
            obj.init_gl(self.shader_cache)
        self.light.init_gl(self.shader_cache)

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

        self.light.render_shadow_map(self)

        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.render_fbo)
        
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glClear(GL.GL_DEPTH_BUFFER_BIT)
        GL.glViewport(0, 0, width, height)

        for obj in self.objects:
            program = obj.program
            GL.glUseProgram(program.program)

            projection_transform = self.camera.projection_transform(float(width) / float(height))
            projection_transform = projection_transform * glm.rotate(math.radians(-90), glm.vec3(1, 0, 0))
            view_transform = self.camera.view_transform()
            
            GL.glUniformMatrix4fv(program.uniform_location('projection_transform'), 1, GL.GL_FALSE, glm.value_ptr(projection_transform))
            GL.glUniformMatrix4fv(program.uniform_location('view_transform'), 1, GL.GL_FALSE, glm.value_ptr(view_transform))
            GL.glUniform3fv(program.uniform_location('light_position'), 1, glm.value_ptr(self.light.position))
            GL.glUniform1f(program.uniform_location('light_intensity'), self.light.intensity)
            GL.glUniform1i(program.uniform_location('shadow_texture'), 0)

            GL.glActiveTexture(GL.GL_TEXTURE0)
            GL.glBindTexture(GL.GL_TEXTURE_CUBE_MAP, self.light.shadow_texture)

            obj.render(program)
            
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
