#version 130

uniform sampler2D frame;

void main()
{
    vec4 color = texelFetch(frame, ivec2(gl_FragCoord.xy), 0);

    gl_FragColor = color;
}