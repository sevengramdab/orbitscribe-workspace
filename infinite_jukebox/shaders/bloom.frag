// Agent 6 — VFX Artist: Multi-Pass Gaussian Bloom
// ================================================
// ELI5: This shader is like a smart-home accent-lighting zone. It finds
// the brightest bulbs in the room, wraps them in a soft glow, and bleeds
// that light onto the neighboring walls so the whole space feels warmer.

precision highp float;
varying vec2 v_uv;

uniform sampler2D u_texture;     // Main image feed from the security camera
uniform vec2 u_texelSize;        // Size of one pixel, like stud spacing
uniform float u_intensity;       // Dimmer knob for glow strength
uniform int u_iteration;         // Which pyramid floor we're rendering

void main () {
    // Calculate sample spacing like setting the throw on a theatrical spotlight.
    vec2 off = u_texelSize * (float(u_iteration) * 2.0 + 1.0);

    // 4-tap Kawase blur: sample the four corners of a square around this pixel,
    // like checking the light levels in the four corners of a room.
    vec4 sum = vec4(0.0);
    sum += texture2D(u_texture, v_uv + vec2(-off.x, -off.y));
    sum += texture2D(u_texture, v_uv + vec2( off.x, -off.y));
    sum += texture2D(u_texture, v_uv + vec2(-off.x,  off.y));
    sum += texture2D(u_texture, v_uv + vec2( off.x,  off.y));
    sum *= 0.25;

    // Extract bright regions: like a photocell that only triggers accent lights
    // when the main chandelier is above 80% brightness.
    vec4 base = texture2D(u_texture, v_uv);
    vec4 bright = max(sum - 0.8, 0.0) * 5.0;

    // Additive composite: wire the glow circuit in parallel with the main lights.
    gl_FragColor = base + bright * u_intensity;
}
