/**
 * Agent 3 / Agent 6 / Agent 9 — WebGL Fluid Engine & Render Loop
 * ================================================================
 * Think of this file as the complete central plant control panel
 * rendered on a touchscreen HMI (Human-Machine Interface). It:
 * 1. Initializes five GPU "pumps" (viewports) via WebGL
 * 2. Runs the physics solver every 16.6 ms (60 Hz PLC scan)
 * 3. Renders the fluid dye to the screen with post-FX
 * 4. Reacts to audio FFT data and touch input
 * 5. Accepts live config updates from the Engineering Dashboard
 *
 * ELI5: Imagine a giant fish tank with colored lights shining through
 * moving water. This code is both the water pump AND the light board:
 * it stirs the water based on music, then paints what you see.
 */

class InfiniteJukeboxFluid {
    constructor(canvas, options = {}) {
        // ELI5: Like choosing between a standard 120V outlet and an
        // industrial 480V three-phase socket. WebGL is the power source
        // that drives the whole visual system.
        this.canvas = canvas;
        this.gl = canvas.getContext('webgl', {
            alpha: true,
            depth: false,
            stencil: false,
            antialias: false,
            preserveDrawingBuffer: false,
            premultipliedAlpha: false,
        });
        if (!this.gl) {
            throw new Error('WebGL not supported — like trying to run a 480V motor on 120V.');
        }

        // --- Configuration — The jobsite commissioning sheet ---
        // ELI5: Before any construction starts, the architect writes down
        // exactly how thick the walls should be, what grade of steel to use,
        // and how many amps each circuit needs. These are those numbers.
        this.simResolution = options.simResolution || 512;
        this.dyeResolution = options.dyeResolution || 1024;
        this.captureRatio = options.captureRatio || 1.0 / window.devicePixelRatio;
        this.dt = options.dt || 0.016;
        this.densityDissipation = options.densityDissipation ?? 0.99;
        this.velocityDissipation = options.velocityDissipation ?? 0.98;
        this.pressureIterations = options.pressureIterations || 20;
        this.curlStrength = options.curlStrength || 30.0;
        this.splatRadius = options.splatRadius || 0.003;
        this.bloomIntensity = options.bloomIntensity ?? 0.3;
        this.sunraysWeight = options.sunraysWeight ?? 1.0;
        this.colorTemp = options.colorTemp ?? 6500.0;
        this.exposure = options.exposure ?? 1.0;
        this.gamma = options.gamma ?? 2.2;
        this.ditherStrength = options.ditherStrength ?? 0.03;

        // --- State ---
        // ELI5: Like the clipboard the foreman carries: who touched what,
        // where the paint sprayer is aimed, and whether the system is running.
        this.pointers = [{ id: -1, x: 0, y: 0, dx: 0, dy: 0, down: false }];
        this.splats = [];
        this.audioFrame = null;
        this.running = false;
        this._frameCount = 0;

        // --- WebGL Resources — The breaker panel and wire pulls ---
        // ELI5: Before an electrician can install outlets, they need to
        // mount the panel, pull Romex through the studs, and label every
        // breaker. These functions do the digital equivalent.
        this._initShaders();
        this._initFramebuffers();
        this._initBlit();

        // --- Resize handler ---
        // ELI5: Like a motorized projection screen that automatically
        // adjusts its size when the conference room table is reconfigured.
        this.resize();
        window.addEventListener('resize', () => this.resize());

        // --- Pointer events (Agent 4) ---
        // ELI5: Motion sensors and touch panels that let a human operator
        // interact with the building automation system directly.
        this._bindPointerEvents();
    }

    // ========================================================================
    // SHADER COMPILATION — The electrical contractor terminating wires
    // ========================================================================
    _initShaders() {
        const gl = this.gl;

        // Helper: compile shader from source string
        // ELI5: Like translating a wiring diagram into actual copper connections.
        const compile = (type, src) => {
            const s = gl.createShader(type);
            gl.shaderSource(s, src);
            gl.compileShader(s);
            if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
                console.error('Shader compile error:', gl.getShaderInfoLog(s));
            }
            return s;
        };

        // Helper: link vertex + fragment into a program
        // ELI5: Like pairing a breaker with its panel slot — both must match.
        const program = (vertSrc, fragSrc) => {
            const p = gl.createProgram();
            gl.attachShader(p, compile(gl.VERTEX_SHADER, vertSrc));
            gl.attachShader(p, compile(gl.FRAGMENT_SHADER, fragSrc));
            gl.linkProgram(p);
            if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
                console.error('Program link error:', gl.getProgramInfoLog(p));
            }
            return p;
        };

        // Minimal fullscreen vertex shader (shared by all passes)
        // ELI5: Like a standardized junction box that every room's outlet
        // wires back to. One shape, reused everywhere.
        const baseVert = `
            attribute vec2 a_position;
            varying vec2 v_uv;
            void main() { v_uv = a_position * 0.5 + 0.5; gl_Position = vec4(a_position, 0.0, 1.0); }
        `;

        // --- Fragment shaders (embedded so this file is self-contained) ---
        // ELI5: In production, these would be fetched from the server. Here we
        // inline them for reliability — like keeping spare fuses in the panel.

        const advectFrag = `
            precision highp float; precision highp sampler2D;
            varying vec2 v_uv;
            uniform sampler2D u_velocity; uniform sampler2D u_source;
            uniform vec2 u_texelSize; uniform float u_dt; uniform float u_dissipation;
            void main() {
                vec2 coord = v_uv - u_dt * texture2D(u_velocity, v_uv).xy * u_texelSize;
                gl_FragColor = u_dissipation * texture2D(u_source, coord);
            }
        `;

        const splatFrag = `
            precision highp float;
            varying vec2 v_uv;
            uniform sampler2D u_target; uniform float u_aspectRatio;
            uniform vec3 u_color; uniform vec2 u_point; uniform float u_radius;
            void main() {
                vec2 p = v_uv - u_point; p.x *= u_aspectRatio;
                float falloff = exp(-dot(p, p) / u_radius);
                vec4 base = texture2D(u_target, v_uv);
                gl_FragColor = base + vec4(u_color, 1.0) * falloff;
            }
        `;

        const curlFrag = `
            precision highp float;
            varying vec2 v_uv;
            uniform sampler2D u_velocity; uniform vec2 u_texelSize;
            void main() {
                float L = texture2D(u_velocity, v_uv - vec2(u_texelSize.x, 0.0)).y;
                float R = texture2D(u_velocity, v_uv + vec2(u_texelSize.x, 0.0)).y;
                float T = texture2D(u_velocity, v_uv + vec2(0.0, u_texelSize.y)).x;
                float B = texture2D(u_velocity, v_uv - vec2(0.0, u_texelSize.y)).x;
                gl_FragColor = vec4(0.5 * (R - L - T + B), 0.0, 0.0, 1.0);
            }
        `;

        const vorticityFrag = `
            precision highp float;
            varying vec2 v_uv;
            uniform sampler2D u_velocity; uniform sampler2D u_curl;
            uniform vec2 u_texelSize; uniform float u_curlStrength; uniform float u_dt;
            void main() {
                float L = texture2D(u_curl, v_uv - vec2(u_texelSize.x, 0.0)).x;
                float R = texture2D(u_curl, v_uv + vec2(u_texelSize.x, 0.0)).x;
                float T = texture2D(u_curl, v_uv + vec2(0.0, u_texelSize.y)).x;
                float B = texture2D(u_curl, v_uv - vec2(0.0, u_texelSize.y)).x;
                float C = texture2D(u_curl, v_uv).x;
                vec2 grad = 0.5 * vec2(abs(R) - abs(L), abs(T) - abs(B));
                grad /= length(grad) + 1e-5;
                vec2 force = u_curlStrength * u_dt * grad * C;
                force.y *= -1.0;
                vec2 vel = texture2D(u_velocity, v_uv).xy;
                gl_FragColor = vec4(vel + force, 0.0, 1.0);
            }
        `;

        const divergenceFrag = `
            precision highp float;
            varying vec2 v_uv;
            uniform sampler2D u_velocity; uniform vec2 u_texelSize;
            void main() {
                float L = texture2D(u_velocity, v_uv - vec2(u_texelSize.x, 0.0)).x;
                float R = texture2D(u_velocity, v_uv + vec2(u_texelSize.x, 0.0)).x;
                float T = texture2D(u_velocity, v_uv + vec2(0.0, u_texelSize.y)).y;
                float B = texture2D(u_velocity, v_uv - vec2(0.0, u_texelSize.y)).y;
                gl_FragColor = vec4(0.5 * (R - L + T - B), 0.0, 0.0, 1.0);
            }
        `;

        const pressureFrag = `
            precision highp float;
            varying vec2 v_uv;
            uniform sampler2D u_pressure; uniform sampler2D u_divergence;
            uniform vec2 u_texelSize;
            void main() {
                float L = texture2D(u_pressure, v_uv - vec2(u_texelSize.x, 0.0)).x;
                float R = texture2D(u_pressure, v_uv + vec2(u_texelSize.x, 0.0)).x;
                float T = texture2D(u_pressure, v_uv + vec2(0.0, u_texelSize.y)).x;
                float B = texture2D(u_pressure, v_uv - vec2(0.0, u_texelSize.y)).x;
                float C = texture2D(u_divergence, v_uv).x;
                gl_FragColor = vec4((L + R + T + B - C) * 0.25, 0.0, 0.0, 1.0);
            }
        `;

        const gradientSubtractFrag = `
            precision highp float;
            varying vec2 v_uv;
            uniform sampler2D u_pressure; uniform sampler2D u_velocity;
            uniform vec2 u_texelSize;
            void main() {
                float L = texture2D(u_pressure, v_uv - vec2(u_texelSize.x, 0.0)).x;
                float R = texture2D(u_pressure, v_uv + vec2(u_texelSize.x, 0.0)).x;
                float T = texture2D(u_pressure, v_uv + vec2(0.0, u_texelSize.y)).x;
                float B = texture2D(u_pressure, v_uv - vec2(0.0, u_texelSize.y)).x;
                vec2 vel = texture2D(u_velocity, v_uv).xy;
                vel -= 0.5 * vec2(R - L, T - B);
                gl_FragColor = vec4(vel, 0.0, 1.0);
            }
        `;

        const displayFrag = `
            precision highp float;
            varying vec2 v_uv;
            uniform sampler2D u_texture; uniform float u_colorTemp;
            uniform float u_exposure; uniform float u_gamma; uniform float u_ditherStrength;
            uniform float u_bloomIntensity; uniform sampler2D u_bloom;
            uniform float u_sunraysWeight;

            vec3 kelvinToRGB(float k) {
                float t = k / 1000.0;
                float r = (t <= 6.5) ? 1.0 : 1.292936186062745 * pow(t - 6.5, -0.1332047592);
                float g = (t <= 8.0) ? 0.832796096 * pow(t - 2.0, -0.0755148492) : 1.35666721 * pow(t - 2.0, 0.234945);
                float b = (t >= 6.5) ? 1.0 : 0.543206789110196 * pow(t - 0.5, 0.454294);
                return clamp(vec3(r, g, b), 0.0, 1.0);
            }

            // Bayer 4x4 ordered dither matrix encoded as floats
            float bayer(vec2 uv) {
                vec2 q = floor(uv * vec2(1024.0));
                int x = int(mod(q.x, 4.0));
                int y = int(mod(q.y, 4.0));
                int i = y * 4 + x;
                // 4x4 bayer pattern: 0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5
                if (i==0) return 0.0;   if (i==1) return 8.0;   if (i==2) return 2.0;   if (i==3) return 10.0;
                if (i==4) return 12.0;  if (i==5) return 4.0;   if (i==6) return 14.0;  if (i==7) return 6.0;
                if (i==8) return 3.0;   if (i==9) return 11.0;  if (i==10) return 1.0;  if (i==11) return 9.0;
                if (i==12) return 15.0; if (i==13) return 7.0;  if (i==14) return 13.0; if (i==15) return 5.0;
                return 0.0;
            }

            void main() {
                vec3 dye = texture2D(u_texture, v_uv).rgb;
                vec3 bloom = texture2D(u_bloom, v_uv).rgb * u_bloomIntensity;
                vec3 bg = vec3(0.015, 0.02, 0.035) + 0.01 * sin(v_uv.xyx * 3.14159);
                vec3 color = (dye + bg + bloom) * kelvinToRGB(u_colorTemp);
                color *= u_exposure;
                color = color / (1.0 + color * 0.15);
                color = pow(max(color, vec3(0.0)), vec3(1.0 / u_gamma));
                // Ordered dither to prevent banding
                float dither = (bayer(gl_FragCoord.xy) / 16.0 - 0.5) * u_ditherStrength;
                color += dither;
                gl_FragColor = vec4(color, 1.0);
            }
        `;

        const bloomPrefilterFrag = `
            precision highp float;
            varying vec2 v_uv;
            uniform sampler2D u_texture;
            void main() {
                vec4 c = texture2D(u_texture, v_uv);
                vec4 b = max(c - 0.8, 0.0) * 5.0;
                gl_FragColor = b;
            }
        `;

        const bloomBlurFrag = `
            precision highp float;
            varying vec2 v_uv;
            uniform sampler2D u_texture; uniform vec2 u_texelSize; uniform vec2 u_direction;
            void main() {
                vec4 sum = vec4(0.0);
                float off[3]; off[0] = -1.3846153846; off[1] = 0.0; off[2] = 1.3846153846;
                float weight[3]; weight[0] = 0.2270270270; weight[1] = 0.3162162162; weight[2] = 0.0702702703;
                for (int i = 0; i < 3; i++) {
                    vec2 o = u_direction * u_texelSize * off[i];
                    sum += texture2D(u_texture, v_uv + o) * weight[i];
                    if (i != 1) sum += texture2D(u_texture, v_uv - o) * weight[i];
                }
                gl_FragColor = sum;
            }
        `;

        // --- Compile and cache programs ---
        // ELI5: Like labeling every breaker in the panel so the electrician
        // doesn't have to guess which switch controls the kitchen.
        this.progAdvect = program(baseVert, advectFrag);
        this.progSplat = program(baseVert, splatFrag);
        this.progCurl = program(baseVert, curlFrag);
        this.progVorticity = program(baseVert, vorticityFrag);
        this.progDivergence = program(baseVert, divergenceFrag);
        this.progPressure = program(baseVert, pressureFrag);
        this.progGradientSubtract = program(baseVert, gradientSubtractFrag);
        this.progDisplay = program(baseVert, displayFrag);
        this.progBloomPrefilter = program(baseVert, bloomPrefilterFrag);
        this.progBloomBlur = program(baseVert, bloomBlurFrag);
    }

    _initFramebuffers() {
        const gl = this.gl;
        // FORCE UNSIGNED_BYTE for maximum compatibility.
        // ELI5: Instead of trying to run 480V three-phase industrial motors,
        // we use standard 120V household outlets that work everywhere.
        const type = gl.UNSIGNED_BYTE;
        const filtering = gl.LINEAR;

        // Helper: create double-buffered FBO (ping-pong)
        // ELI5: Like having two whiteboards. You read from one while
        // writing on the other, then swap them for the next meeting.
        const createDoubleFBO = (w, h, channels) => {
            let fbo1 = this._createFBO(w, h, channels, type, filtering);
            let fbo2 = this._createFBO(w, h, channels, type, filtering);
            return {
                width: w, height: h,
                read: () => fbo1,
                write: () => fbo2,
                swap: () => { const t = fbo1; fbo1 = fbo2; fbo2 = t; }
            };
        };

        this.velocity = createDoubleFBO(this.simResolution, this.simResolution, 2);
        this.density  = createDoubleFBO(this.dyeResolution, this.dyeResolution, 4);
        this.divergence = this._createFBO(this.simResolution, this.simResolution, 4, type, gl.NEAREST);
        this.curl     = this._createFBO(this.simResolution, this.simResolution, 4, type, gl.NEAREST);
        this.pressure = createDoubleFBO(this.simResolution, this.simResolution, 2);

        // Bloom buffers (half resolution)
        // ELI5: Like running a dimmer circuit at half voltage so you can
        // smoothly fade the accent lights without overloading the transformer.
        const bw = this.dyeResolution >> 1;
        const bh = this.dyeResolution >> 1;
        this.bloom = createDoubleFBO(bw, bh, 4);
    }

    _createFBO(w, h, channels, type, filtering) {
        const gl = this.gl;
        const internalFormat = gl.RGBA;
        const format = gl.RGBA;

        const texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.texImage2D(gl.TEXTURE_2D, 0, internalFormat, w, h, 0, format, type, null);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filtering);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filtering);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);

        const fbo = gl.createFramebuffer();
        gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, texture, 0);

        // Check if the GPU can actually render to this texture format.
        // ELI5: Like testing a breaker before energizing the panel —
        // if it trips immediately, you know the wiring is wrong.
        const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);

        if (status !== gl.FRAMEBUFFER_COMPLETE) {
            console.warn(`[Jukebox] FBO incomplete with type ${type} (${status}). Falling back to UNSIGNED_BYTE.`);
            gl.deleteTexture(texture);
            gl.deleteFramebuffer(fbo);
            return this._createFBO(w, h, channels, gl.UNSIGNED_BYTE, filtering);
        }

        return { texture, fbo, width: w, height: h };
    }

    _initBlit() {
        // Fullscreen triangle (more efficient than quad)
        // ELI5: Instead of drawing a rectangle with four corners, we draw
        // a giant triangle that covers the whole screen. It's like using
        // one long fluorescent tube instead of four recessed cans.
        const gl = this.gl;
        this.blitVao = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, this.blitVao);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, -1, 3, 3, -1]), gl.STATIC_DRAW);
    }

    // ========================================================================
    // RENDERING UTILITIES — The multimeter and wire stripper
    // ========================================================================
    _bindFBO(target) {
        // ELI5: Like switching a multimeter from measuring voltage to
        // measuring current — you have to tell the tool which port to read.
        const gl = this.gl;
        gl.bindFramebuffer(gl.FRAMEBUFFER, target.fbo);
        gl.viewport(0, 0, target.width, target.height);
    }

    _blit(program, uniforms = {}) {
        // ELI5: Like flipping a series of light switches in the correct
        // order so the stage lights come on with the right color gels.
        const gl = this.gl;
        gl.useProgram(program);
        gl.bindBuffer(gl.ARRAY_BUFFER, this.blitVao);
        const posLoc = gl.getAttribLocation(program, 'a_position');
        gl.enableVertexAttribArray(posLoc);
        gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

        let texUnit = 0;
        for (const [name, val] of Object.entries(uniforms)) {
            const loc = gl.getUniformLocation(program, name);
            if (loc === null) continue;
            if (val instanceof WebGLTexture) {
                gl.activeTexture(gl.TEXTURE0 + texUnit);
                gl.bindTexture(gl.TEXTURE_2D, val);
                gl.uniform1i(loc, texUnit);
                texUnit++;
            } else if (typeof val === 'number') gl.uniform1f(loc, val);
            else if (typeof val === 'boolean') gl.uniform1i(loc, val ? 1 : 0);
            else if (Array.isArray(val) || val instanceof Float32Array) {
                if (val.length === 2) gl.uniform2f(loc, val[0], val[1]);
                else if (val.length === 3) gl.uniform3f(loc, val[0], val[1], val[2]);
                else if (val.length === 4) gl.uniform4f(loc, val[0], val[1], val[2], val[3]);
            }
        }
        gl.drawArrays(gl.TRIANGLES, 0, 3);
    }

    // ========================================================================
    // CONFIG UPDATE — Live-tweak from the Engineering Dashboard
    // ========================================================================
    applyConfig(config) {
        // ELI5: Like a facilities manager walking into the mechanical room
        // and adjusting thermostat setpoints without shutting down the chiller.
        if (config.viscosity !== undefined) {
            // In WebGL sim, viscosity is approximated via dissipation
            this.velocityDissipation = 0.95 + (config.viscosity * 0.04);
            this.densityDissipation = 0.97 + (config.viscosity * 0.02);
        }
        if (config.flowVelocity !== undefined) {
            // Scale the dt multiplier for faster/slower simulation
            this.dt = 0.016 * Math.max(0.5, Math.min(2.0, config.flowVelocity));
        }
        if (config.curlStrength !== undefined) this.curlStrength = config.curlStrength;
        if (config.pressureIterations !== undefined) this.pressureIterations = Math.floor(config.pressureIterations);
        if (config.bloomIntensity !== undefined) this.bloomIntensity = config.bloomIntensity;
        if (config.sunraysWeight !== undefined) this.sunraysWeight = config.sunraysWeight;
        if (config.colorTemp !== undefined) this.colorTemp = config.colorTemp;
        if (config.exposure !== undefined) this.exposure = config.exposure;
        if (config.gamma !== undefined) this.gamma = config.gamma;
        if (config.ditherStrength !== undefined) this.ditherStrength = config.ditherStrength;
        if (config.splatRadius !== undefined) this.splatRadius = config.splatRadius;
    }

    // ========================================================================
    // SIMULATION STEP — One full PLC scan cycle
    // ========================================================================
    step() {
        const gl = this.gl;
        const w = this.simResolution;
        const h = this.simResolution;
        const texel = [1.0 / w, 1.0 / h];

        // --- 0. SEED INITIAL COLOR if fields are empty ---
        // ELI5: Before the city water show starts, the techs add a little
        // dye to the reservoir so the first spray isn't invisible clear water.
        this._frameCount++;
        if (this._frameCount < 60) {
            const t = this._frameCount / 60;
            this.splats.push({
                x: 0.5 + 0.3 * Math.cos(t * 6.28),
                y: 0.5 + 0.3 * Math.sin(t * 6.28),
                vx: Math.cos(t * 6.28) * 2.0,
                vy: Math.sin(t * 6.28) * 2.0,
                color: [1.0, 0.4, 0.2],
                radius: 0.05,
            });
        }

        // --- 1. SPLAT (audio & pointer forces) ---
        // ELI5: Open every fire hydrant scheduled for this frame.
        for (const splat of this.splats) {
            this._splat(splat);
        }
        this.splats = [];

        // --- 2. ADVECT VELOCITY ---
        // "Carry the current downstream"
        this._bindFBO(this.velocity.write());
        this._blit(this.progAdvect, {
            u_velocity: this.velocity.read().texture,
            u_source: this.velocity.read().texture,
            u_texelSize: texel,
            u_dt: this.dt,
            u_dissipation: this.velocityDissipation,
        });
        this.velocity.swap();

        // --- 3. CURL & VORTICITY ---
        // "Measure swirl, then boost it"
        this._bindFBO(this.curl);
        this._blit(this.progCurl, {
            u_velocity: this.velocity.read().texture,
            u_texelSize: texel,
        });

        this._bindFBO(this.velocity.write());
        this._blit(this.progVorticity, {
            u_velocity: this.velocity.read().texture,
            u_curl: this.curl.texture,
            u_texelSize: texel,
            u_curlStrength: this.curlStrength,
            u_dt: this.dt,
        });
        this.velocity.swap();

        // --- 4. DIVERGENCE ---
        // "Count water entering vs leaving"
        this._bindFBO(this.divergence);
        this._blit(this.progDivergence, {
            u_velocity: this.velocity.read().texture,
            u_texelSize: texel,
        });

        // --- 5. PRESSURE JACOBI ---
        // "Walk the building until pressure balances"
        for (let i = 0; i < this.pressureIterations; i++) {
            this._bindFBO(this.pressure.write());
            this._blit(this.progPressure, {
                u_pressure: this.pressure.read().texture,
                u_divergence: this.divergence.texture,
                u_texelSize: texel,
            });
            this.pressure.swap();
        }

        // --- 6. GRADIENT SUBTRACT ---
        // "Install pressure-balancing valve"
        this._bindFBO(this.velocity.write());
        this._blit(this.progGradientSubtract, {
            u_pressure: this.pressure.read().texture,
            u_velocity: this.velocity.read().texture,
            u_texelSize: texel,
        });
        this.velocity.swap();

        // --- 7. ADVECT DYE ---
        // "Carry the food coloring downstream"
        const dtexel = [1.0 / this.dyeResolution, 1.0 / this.dyeResolution];
        this._bindFBO(this.density.write());
        this._blit(this.progAdvect, {
            u_velocity: this.velocity.read().texture,
            u_source: this.density.read().texture,
            u_texelSize: dtexel,
            u_dt: this.dt,
            u_dissipation: this.densityDissipation,
        });
        this.density.swap();
    }

    _splat(splat) {
        // ELI5: Like connecting a paint sprayer to a compressor and
        // pulling the trigger at a specific spot on the wall.
        const aspect = this.canvas.width / this.canvas.height;
        // Velocity injection
        this._bindFBO(this.velocity.write());
        this._blit(this.progSplat, {
            u_target: this.velocity.read().texture,
            u_aspectRatio: aspect,
            u_color: [splat.vx, splat.vy, 0.0],
            u_point: [splat.x, splat.y],
            u_radius: this.splatRadius,
        });
        this.velocity.swap();

        // Dye injection
        this._bindFBO(this.density.write());
        this._blit(this.progSplat, {
            u_target: this.density.read().texture,
            u_aspectRatio: aspect,
            u_color: splat.color,
            u_point: [splat.x, splat.y],
            u_radius: this.splatRadius,
        });
        this.density.swap();
    }

    // ========================================================================
    // DISPLAY — The final lighting board scene
    // ========================================================================
    render() {
        const gl = this.gl;

        // Bloom prefilter
        // ELI5: Like putting a polarizing filter on a camera lens so only
        // the brightest highlights get through for the glare effect.
        this._bindFBO(this.bloom.write());
        this._blit(this.progBloomPrefilter, {
            u_texture: this.density.read().texture,
        });
        this.bloom.swap();

        // Bloom blur passes (horizontal + vertical)
        // ELI5: Like shining a flashlight through frosted glass — the light
        // spreads out horizontally first, then vertically, creating a soft glow.
        const bt = [1.0 / (this.dyeResolution >> 1), 1.0 / (this.dyeResolution >> 1)];
        this._bindFBO(this.bloom.write());
        this._blit(this.progBloomBlur, {
            u_texture: this.bloom.read().texture,
            u_texelSize: bt,
            u_direction: [1, 0],
        });
        this.bloom.swap();

        this._bindFBO(this.bloom.write());
        this._blit(this.progBloomBlur, {
            u_texture: this.bloom.read().texture,
            u_texelSize: bt,
            u_direction: [0, 1],
        });
        this.bloom.swap();

        // Composite to screen
        // ELI5: Like the lighting director's final cue: all dimmers, color
        // wheels, and gobos set to their show positions before curtain rise.
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.viewport(0, 0, this.canvas.width, this.canvas.height);
        this._blit(this.progDisplay, {
            u_texture: this.density.read().texture,
            u_bloom: this.bloom.read().texture,
            u_colorTemp: this.colorTemp,
            u_exposure: this.exposure,
            u_gamma: this.gamma,
            u_ditherStrength: this.ditherStrength,
            u_bloomIntensity: this.bloomIntensity,
            u_sunraysWeight: this.sunraysWeight,
        });
    }

    // ========================================================================
    // INPUT HANDLING — Touch, mouse, and audio
    // ========================================================================
    _bindPointerEvents() {
        // ELI5: Like installing motion sensors and touch panels throughout
        // the building so the automation system can react to human presence.
        const c = this.canvas;
        const getUV = (e) => {
            const rect = c.getBoundingClientRect();
            return [
                (e.clientX - rect.left) / rect.width,
                1.0 - (e.clientY - rect.top) / rect.height,
            ];
        };

        c.addEventListener('mousedown', (e) => {
            const [x, y] = getUV(e);
            this.pointers[0] = { id: 0, x, y, dx: 0, dy: 0, down: true };
        });
        window.addEventListener('mousemove', (e) => {
            if (!this.pointers[0].down) return;
            const [x, y] = getUV(e);
            const p = this.pointers[0];
            p.dx = (x - p.x) * 10;
            p.dy = (y - p.y) * 10;
            p.x = x; p.y = y;
            this.splats.push({ x: p.x, y: p.y, vx: p.dx, vy: p.dy, color: [1,1,1] });
        });
        window.addEventListener('mouseup', () => { this.pointers[0].down = false; });

        // Touch support
        c.addEventListener('touchstart', (e) => {
            e.preventDefault();
            for (let t of e.changedTouches) {
                const [x, y] = getUV(t);
                this.pointers.push({ id: t.identifier, x, y, dx: 0, dy: 0, down: true });
            }
        }, { passive: false });
        c.addEventListener('touchmove', (e) => {
            e.preventDefault();
            for (let t of e.changedTouches) {
                const p = this.pointers.find(p => p.id === t.identifier);
                if (!p) continue;
                const [x, y] = getUV(t);
                p.dx = (x - p.x) * 10;
                p.dy = (y - p.y) * 10;
                p.x = x; p.y = y;
                this.splats.push({ x: p.x, y: p.y, vx: p.dx, vy: p.dy, color: [1,1,1] });
            }
        }, { passive: false });
        c.addEventListener('touchend', (e) => {
            for (let t of e.changedTouches) {
                const p = this.pointers.find(p => p.id === t.identifier);
                if (p) p.down = false;
            }
        });
    }

    feedAudioFrame(frame) {
        // Convert FFT frame into splats
        // ELI5: The spectrum analyzer has 512 LEDs. Each lit LED tells us
        // to open a tiny misting nozzle at a certain horizontal position.
        const bins = frame.frequencyBins;
        const n = bins.length;

        // 5 audio channels mapped to fluid injection zones
        // ELI5: Like having five separate sprinkler zones controlled by
        // different valves: lawn (bass), shrubs (low mid), flower beds (mid),
        // driveway (high mid), and patio misters (treble).
        const channels = [
            { range: [0.0, 0.08], color: [0.9, 0.2, 0.1] },   // Bass
            { range: [0.08, 0.16], color: [0.8, 0.5, 0.1] },  // Low mid
            { range: [0.16, 0.35], color: [0.2, 0.8, 0.3] },  // Mid
            { range: [0.35, 0.60], color: [0.2, 0.5, 0.9] },  // High mid
            { range: [0.60, 1.00], color: [0.6, 0.2, 0.9] },  // Treble
        ];

        for (let ci = 0; ci < channels.length; ci++) {
            const ch = channels[ci];
            const lo = Math.floor(ch.range[0] * n);
            const hi = Math.floor(ch.range[1] * n);
            let energy = 0;
            for (let i = lo; i < hi; i++) energy += bins[i];
            energy /= (hi - lo) + 1e-6;

            if (energy < 0.02) continue;

            const cx = (lo + hi) * 0.5 / n;
            const cy = 0.5 + 0.15 * Math.sin(performance.now() * 0.002 + ci);
            this.splats.push({
                x: cx, y: cy,
                vx: energy * 6.0 * (ci % 2 === 0 ? 1 : -1),
                vy: -energy * 8.0,
                color: [ch.color[0] * 1.5, ch.color[1] * 1.5, ch.color[2] * 1.5],
                radius: 0.008 + energy * 0.025,
                density: Math.min(1.0, energy * 3.0),
            });
        }
    }

    resize() {
        // ELI5: Like a motorized projection screen that automatically
        // adjusts when the conference room layout changes.
        const dpr = window.devicePixelRatio || 1;
        const displayW = Math.round(this.canvas.clientWidth * dpr);
        const displayH = Math.round(this.canvas.clientHeight * dpr);
        this.canvas.width = displayW;
        this.canvas.height = displayH;
    }

    // ========================================================================
    // MAIN LOOP — The central plant HMI refresh
    // ========================================================================
    start() {
        // ELI5: Like pressing the green "AUTO" button on a building
        // automation system: chillers start, dampers open, scan begins.
        if (this.running) return;
        this.running = true;
        const loop = () => {
            if (!this.running) return;
            this.step();
            this.render();
            requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
    }

    stop() {
        // ELI5: Like an orderly shutdown sequence: close dampers, stop fans,
        // then kill power to the mechanical room.
        this.running = false;
    }
}

// ========================================================================
// Bootstrap — Wire everything together like a home-automation panel
// ========================================================================
function initInfiniteJukebox() {
    // ELI5: Like the commissioning technician who walks through a new
    // smart home, pairing every switch to its hub and testing every scene.
    const canvas = document.getElementById('fluid-canvas');
    if (!canvas) {
        console.error('Missing #fluid-canvas — like a panel with no drywall cutout.');
        return;
    }

    const fluid = new InfiniteJukeboxFluid(canvas, {
        simResolution: 256,
        dyeResolution: 1024,
        pressureIterations: 20,
        curlStrength: 30,
    });

    const audio = new InfiniteJukeboxAudio({ fftSize: 512, bpm: 110 });

    // Connect audio → fluid
    // ELI5: Like running a low-voltage wire from the doorbell transformer
    // to the chime — when the button is pressed, the chime rings.
    audio.onAudioFrame(frame => fluid.feedAudioFrame(frame));

    // Auto-start on load — visualizer runs immediately, audio tries best-effort
    fluid.start();
    (async () => {
        try {
            await audio.start();
        } catch (audioErr) {
            console.warn('[Jukebox] AudioContext resume blocked (autoplay policy):', audioErr);
        }
    })();
    const status = document.getElementById('status');
    if (status) {
        status.textContent = '● Live';
        status.classList.add('live');
    }

    // Expose to global for dashboard integration
    // ELI5: Like labeling every breaker in the panel with a Sharpie so
    // the next technician knows which switch controls what.
    window.jukeboxFluid = fluid;
    window.jukeboxAudio = audio;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initInfiniteJukebox);
} else {
    initInfiniteJukebox();
}
