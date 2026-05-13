// Agent 4 — UX Engineer: Force & Dye Injection (The Fire Hydrant)
// =================================================================
// ELI5: This is the shader equivalent of opening a fire hydrant.
// You specify WHERE (u_point), HOW HARD (u_velocity), WHAT COLOR
// (u_color), and HOW WIDE (u_radius). The shader paints a soft
// Gaussian blob — like a spray nozzle with an adjustable tip.

precision highp float;
varying vec2 v_uv;

uniform sampler2D u_target;       // The fluid field we're injecting into
uniform float u_aspectRatio;      // Screen width / height so the blob stays round
uniform vec3 u_color;             // RGB dye pigment
uniform vec2 u_point;             // Center of the splat in UV space
uniform float u_radius;           // Nozzle orifice diameter
uniform vec2 u_velocity;          // Momentum vector (how hard we push)

void main () {
    // Measure distance from splat center, correcting for aspect ratio,
    // like using a radius gauge on an elliptical duct: you must
    // account for stretch so your measurement is true.
    vec2 p = v_uv - u_point;
    p.x *= u_aspectRatio;
    float dist = length(p);

    // Gaussian falloff: bright in the center, fading at edges,
    // like a theatrical Fresnel fixture with a hot spot and smooth beam edge.
    float falloff = exp(-dist * dist / u_radius);

    // Read existing fluid state at this pixel.
    vec4 base = texture2D(u_target, v_uv);

    // Add the injection scaled by falloff,
    // like opening a valve only partway based on how far the outlet is.
    gl_FragColor = base + vec4(u_color * falloff, falloff);
}
