// Agent 2 — Physicist: Vorticity (Curl) Measurement
// ==================================================
// ELI5: Put a tiny paddlewheel in a stream. If the water on the
// right pushes harder than the left, the wheel spins clockwise.
// That spin rate IS the curl. This shader builds a map of every
// paddlewheel's RPM across the whole river.

precision highp float;
varying vec2 v_uv;

uniform sampler2D u_velocity;
uniform vec2 u_texelSize;

void main () {
    // Sample neighbors: like reading four pressure gauges
    // arranged in a square around the test point.
    float L = texture2D(u_velocity, v_uv - vec2(u_texelSize.x, 0.0)).y;
    float R = texture2D(u_velocity, v_uv + vec2(u_texelSize.x, 0.0)).y;
    float T = texture2D(u_velocity, v_uv + vec2(0.0, u_texelSize.y)).x;
    float B = texture2D(u_velocity, v_uv - vec2(0.0, u_texelSize.y)).x;

    // Curl = dVy/dx - dVx/dy
    // ELI5: (Right push - Left push) minus (Top push - Bottom push)
    float vorticity = R - L - T + B;
    gl_FragColor = vec4(0.5 * vorticity, 0.0, 0.0, 1.0);
}
