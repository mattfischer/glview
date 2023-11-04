#version 130
attribute highp vec3 position;
attribute highp vec3 normal;
attribute highp vec2 texcoord;
uniform mat4 projection_transform;
uniform mat4 view_transform;
uniform mat4 model_transform;
varying vec3 frag_pos;
varying vec3 frag_normal;
varying vec2 frag_texcoord;

void main()
{
    gl_Position = projection_transform * view_transform * model_transform * vec4(position, 1);
    frag_pos = (model_transform * vec4(position, 1)).xyz;
    frag_normal = normal;
    frag_texcoord = texcoord;
}