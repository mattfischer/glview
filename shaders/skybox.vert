#version 410
layout(location = 0) in highp vec3 position;

uniform mat4 projection_transform;
uniform mat4 view_transform;

varying vec3 frag_pos;

void main()
{
    frag_pos = position.xyz;

    vec4 transformed = projection_transform * view_transform * vec4(position, 0);
    gl_Position = vec4(transformed.xy, transformed.w, transformed.w);
}