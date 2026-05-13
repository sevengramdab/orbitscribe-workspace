// Agent 2 — Physicist: Divergence (Source/Sink Detection)
// ========================================================
// ELI5: Imagine a junction box with four conduits entering.
// If 10 amps flow IN and only 8 amps flow OUT, the junction
// is a SOURCE (positive divergence). This shader computes that
// electrical imbalance for every pixel in the fluid grid.

precision highp float;
varying vec2 v_uv;

uniform sampler2D u_velocity;
uniform vec2 u_texelSize;

void main () {
    // Sample four neighbors: like clamping an ammeter on each conduit.
    float L = texture2D(u_velocity, v_uv - vec2(u_texelSize.x, 0.0)).x;
    float R = texture2D(u_velocity, v_uv + vec2(u_texelSize.x, 0.0)).x;
    float T = texture2D(u_velocity, v_uv + vec2(0.0, u_texelSize.y)).y;
    float B = texture2D(u_velocity, v_uv - vec2(0.0, u_texelSize.y)).y;

    // Divergence = dVx/dx + dVy/dy
    float div = 0.5 * (R - L + T - B);
    gl_FragColor = vec4(div, 0.0, 0.0, 1.0);
}
