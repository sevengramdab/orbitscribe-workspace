// Agent 2 — Physicist: Jacobi Pressure Solver (Balancing the Manifold)
// =====================================================================
// ELI5: A hydronic heating system has a balancing valve at every
// radiator. This shader is one walk around the building: each pixel
// averages its four neighbors and subtracts the known divergence.
// We run it 20–80 times per frame until the pressure settles.

precision highp float;
varying vec2 v_uv;

uniform sampler2D u_pressure;
uniform sampler2D u_divergence;
uniform vec2 u_texelSize;

void main () {
    // Read the four adjacent pressure sensors.
    float L = texture2D(u_pressure, v_uv - vec2(u_texelSize.x, 0.0)).x;
    float R = texture2D(u_pressure, v_uv + vec2(u_texelSize.x, 0.0)).x;
    float T = texture2D(u_pressure, v_uv + vec2(0.0, u_texelSize.y)).x;
    float B = texture2D(u_pressure, v_uv - vec2(0.0, u_texelSize.y)).x;
    float C = texture2D(u_divergence, v_uv).x;

    // Jacobi update: new pressure = average(neighbors) - divergence / 4
    // ELI5: If a room is too hot (high divergence), open its valve
    // a little more than the average of its four neighbors.
    float p = (L + R + T + B - C) * 0.25;
    gl_FragColor = vec4(p, 0.0, 0.0, 1.0);
}
