#version 130

vec4 verts[4] = vec4[](
    vec4(-1, -1,  1,  1),
    vec4( 1, -1,  1,  1),
    vec4( 1,  1,  1,  1),
    vec4(-1,  1,  1,  1)
);

void main()
{
    gl_Position = verts[gl_VertexID];
}