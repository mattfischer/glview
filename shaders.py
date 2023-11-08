from OpenGL import GL
import sys

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

