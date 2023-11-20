import glm
from OpenGL import GL

from shaders import ShaderCache

import math

CUBE_FACES = [
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_X,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_X,
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Y,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Y,
    GL.GL_TEXTURE_CUBE_MAP_POSITIVE_Z,
    GL.GL_TEXTURE_CUBE_MAP_NEGATIVE_Z,
]

class Light:
    def __init__(self, position: glm.vec3, intensity: float):
        self.position = position
        self.need_shadow_render = True
        self.intensity = intensity

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

    def render_shadow_map(self, scene: 'Scene'):
        if not self.need_shadow_render:
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
            view_transform = view_transform * glm.translate(-self.position)
            
            GL.glUniformMatrix4fv(self.shadow_program.uniform_location('projection_transform'), 1, False, glm.value_ptr(projection_transform))
            GL.glUniformMatrix4fv(self.shadow_program.uniform_location('view_transform'), 1, False, glm.value_ptr(view_transform))

            for obj in scene.objects:
                obj.render(self.shadow_program)
        
        GL.glUseProgram(0)

        self.need_shadow_render = False
