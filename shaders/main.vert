#version 410
layout(location = 0) in highp vec3 position;
layout(location = 1) in highp vec3 normal;
layout(location = 2) in highp vec2 texcoord;

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
    frag_normal = (model_transform * vec4(normal, 0)).xyz;
    frag_texcoord = texcoord;
}