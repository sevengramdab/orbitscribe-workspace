// Agent 2 — Physicist: Vorticity Confinement (The Eductor Jet)
// =============================================================
// ELI5: In a hydronic heating system, an eductor jet re-injects
// turbulence so the heat exchanger stays efficient. This shader
// does the same: it finds tiny swirls that numerical friction
// is killing, then gives them a kick so they keep spinning.

precision highp float;
varying vec2 v_uv;

uniform sampler2D u_velocity;
uniform sampler2D u_curl;
uniform vec2 u_texelSize;
uniform float u_curlStrength;
uniform float u_dt;

void main () {
    // Measure curl at neighbors to find the center of the swirl.
    float L = texture2D(u_curl, v_uv - vec2(u_texelSize.x, 0.0)).x;
    float R = texture2D(u_curl, v_uv + vec2(u_texelSize.x, 0.0)).x;
    float T = texture2D(u_curl, v_uv + vec2(0.0, u_texelSize.y)).x;
    float B = texture2D(u_curl, v_uv - vec2(0.0, u_texelSize.y)).x;
    float C = texture2D(u_curl, v_uv).x;

    // Gradient of |curl|: points toward the vortex core.
    vec2 grad = 0.5 * vec2(abs(R) - abs(L), abs(T) - abs(B));

    // Normalize to unit length, like calibrating a pressure transducer.
    grad /= length(grad) + 1e-5;

    // Force vector = gradient rotated 90° × curl × strength × dt
    // ELI5: Push perpendicular to the swirl center, like stirring
    // a cup of coffee: your spoon moves at a right angle to the center.
    vec2 force = u_curlStrength * u_dt * grad * C;
    force.y *= -1.0; // Correct handedness for UV space

    // Add force to existing velocity.
    vec2 vel = texture2D(u_velocity, v_uv).xy;
    gl_FragColor = vec4(vel + force, 0.0, 1.0);
}
