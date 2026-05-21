/**
 * ACE-Step V1.5 Integration — Fighter Jet Cockpit Extension
 * ==========================================================
 * Like adding a new MFD page that controls the external music-generation
 * drone (ACE-Step) and pipes its audio into the fighter-jet's
 * heads-up-display visualizer.
 */

class AceStepController {
    constructor() {
        this.host = 'http://127.0.0.1:58080';
        this._injectPanel();
        this._bindControls();
        this._audioCtx = null;
        this._analyser = null;
        this._source = null;
        this._gain = null;
        this._pending = false;
        this._pollInterval = null;
    }

    // ------------------------------------------------------------------
    // Inject ACE-Step section into dashboard
    // ------------------------------------------------------------------
    _injectPanel() {
        const panel = document.getElementById('dash-panel');
        if (!panel) return;

        const section = document.createElement('div');
        section.className = 'dash-section';
        section.id = 'acestep-section';
        section.innerHTML = `
            <div class="dash-section-title">ACE-Step V1.5 Studio</div>
            <div id="acestep-status" style="font-family:var(--jet-mono);font-size:0.7rem;color:var(--jet-muted);margin-bottom:0.5rem;">Checking studio...</div>

            <div class="control-row">
                <div class="control-label"><span>Music Caption</span></div>
                <textarea id="acestep-caption" rows="2" style="width:100%;background:rgba(6,10,14,0.8);border:1px solid var(--jet-panel-border);color:var(--jet-text);font-family:var(--jet-font);font-size:0.75rem;padding:0.4rem;resize:vertical;">A peaceful acoustic guitar melody with soft vocals</textarea>
            </div>

            <div class="control-row">
                <div class="control-label"><span>Lyrics</span></div>
                <textarea id="acestep-lyrics" rows="2" style="width:100%;background:rgba(6,10,14,0.8);border:1px solid var(--jet-panel-border);color:var(--jet-text);font-family:var(--jet-font);font-size:0.75rem;padding:0.4rem;resize:vertical;"></textarea>
            </div>

            <div class="control-row">
                <div class="control-label"><span>BPM</span><span id="val-acestep-bpm" class="control-value">120</span></div>
                <input type="range" id="slider-acestep-bpm" min="60" max="180" value="120">
            </div>

            <div class="control-row">
                <div class="control-label"><span>Key</span></div>
                <select id="select-acestep-key" class="dash-select">
                    <option value="">Auto</option>
                    <option value="C major">C major</option>
                    <option value="G major">G major</option>
                    <option value="D major">D major</option>
                    <option value="A major">A major</option>
                    <option value="E major">E major</option>
                    <option value="F major">F major</option>
                    <option value="Bb major">Bb major</option>
                    <option value="Eb major">Eb major</option>
                    <option value="A minor">A minor</option>
                    <option value="E minor">E minor</option>
                    <option value="D minor">D minor</option>
                    <option value="G minor">G minor</option>
                    <option value="C minor">C minor</option>
                    <option value="F minor">F minor</option>
                    <option value="B minor">B minor</option>
                </select>
            </div>

            <div class="control-row">
                <div class="control-label"><span>DiT Steps</span><span id="val-acestep-steps" class="control-value">50</span></div>
                <input type="range" id="slider-acestep-steps" min="1" max="200" value="50">
            </div>

            <div class="control-row">
                <div class="control-label"><span>Guidance Scale</span><span id="val-acestep-guidance" class="control-value">7.0</span></div>
                <input type="range" id="slider-acestep-guidance" min="10" max="150" value="70">
            </div>

            <div class="control-row">
                <div class="control-label"><span>LM Codes Strength</span><span id="val-acestep-lm" class="control-value">1.00</span></div>
                <input type="range" id="slider-acestep-lm" min="0" max="100" value="100">
            </div>

            <div class="control-row">
                <div class="control-label"><span>Duration (sec)</span><span id="val-acestep-duration" class="control-value">20</span></div>
                <input type="range" id="slider-acestep-duration" min="5" max="60" value="20">
            </div>

            <div class="control-row">
                <div class="control-label"><span>Shift</span><span id="val-acestep-shift" class="control-value">3.0</span></div>
                <input type="range" id="slider-acestep-shift" min="10" max="50" value="30">
            </div>

            <div class="control-row">
                <div class="control-label"><span>LM Temperature</span><span id="val-acestep-temp" class="control-value">0.85</span></div>
                <input type="range" id="slider-acestep-temp" min="0" max="200" value="85">
            </div>

            <div class="auto-dj-row" style="margin-top:0.75rem;">
                <button id="btn-acestep-generate" class="breaker-reset" style="border-color:var(--jet-cyan);color:var(--jet-cyan);flex:2;">Generate Track</button>
                <button id="btn-acestep-autodj" class="breaker-reset" style="border-color:var(--jet-green);color:var(--jet-green);">Auto DJ</button>
            </div>

            <div id="acestep-launch-row" class="auto-dj-row" style="margin-top:0.5rem;display:none;">
                <button id="btn-acestep-launch" class="breaker-reset" style="border-color:var(--jet-yellow);color:var(--jet-yellow);width:100%;">Install & Launch ACE-Step Studio</button>
            </div>
            <div id="acestep-result" style="margin-top:0.5rem;font-family:var(--jet-mono);font-size:0.65rem;color:var(--jet-muted);min-height:1.2em;"></div>
            <audio id="acestep-player" controls style="width:100%;margin-top:0.5rem;display:none;" crossorigin="anonymous"></audio>
        `;

        // Insert before the last element (or append)
        const body = panel.querySelector('.dashboard-body');
        if (body) body.appendChild(section);

        // Add slider styles if missing
        const style = document.createElement('style');
        style.textContent = `
            #acestep-section .control-row { margin-bottom: 0.4rem; }
            #acestep-section textarea:focus { border-color: var(--jet-cyan); outline: none; }
        `;
        document.head.appendChild(style);
    }

    // ------------------------------------------------------------------
    // Bind controls
    // ------------------------------------------------------------------
    _bindControls() {
        // Sliders
        const sliders = [
            { id: 'slider-acestep-bpm', readout: 'val-acestep-bpm', fixed: 0 },
            { id: 'slider-acestep-steps', readout: 'val-acestep-steps', fixed: 0 },
            { id: 'slider-acestep-guidance', readout: 'val-acestep-guidance', fixed: 1, scale: 0.1 },
            { id: 'slider-acestep-lm', readout: 'val-acestep-lm', fixed: 2, scale: 0.01 },
            { id: 'slider-acestep-duration', readout: 'val-acestep-duration', fixed: 0 },
            { id: 'slider-acestep-shift', readout: 'val-acestep-shift', fixed: 1, scale: 0.1 },
            { id: 'slider-acestep-temp', readout: 'val-acestep-temp', fixed: 2, scale: 0.01 },
        ];
        for (const s of sliders) {
            const el = document.getElementById(s.id);
            const ro = document.getElementById(s.readout);
            if (!el || !ro) continue;
            el.addEventListener('input', () => {
                const val = s.scale ? (parseFloat(el.value) * s.scale).toFixed(s.fixed) : parseInt(el.value);
                ro.textContent = val;
            });
        }

        // Buttons
        const genBtn = document.getElementById('btn-acestep-generate');
        const autoBtn = document.getElementById('btn-acestep-autodj');
        const launchBtn = document.getElementById('btn-acestep-launch');
        if (genBtn) genBtn.addEventListener('click', () => this._generate());
        if (autoBtn) autoBtn.addEventListener('click', () => this._autoDJ());
        if (launchBtn) launchBtn.addEventListener('click', () => this._launchStudio());

        // Check status
        this._checkStatus();
        setInterval(() => this._checkStatus(), 10000);
    }

    // ------------------------------------------------------------------
    // Gather params from UI
    // ------------------------------------------------------------------
    _gatherParams() {
        return {
            music_caption: document.getElementById('acestep-caption')?.value || '',
            lyrics: document.getElementById('acestep-lyrics')?.value || '',
            bpm: parseFloat(document.getElementById('slider-acestep-bpm')?.value || 120),
            key: document.getElementById('select-acestep-key')?.value || '',
            dit_inference_steps: parseFloat(document.getElementById('slider-acestep-steps')?.value || 50),
            dit_guidance_scale: parseFloat(document.getElementById('slider-acestep-guidance')?.value || 70) * 0.1,
            lm_codes_strength: parseFloat(document.getElementById('slider-acestep-lm')?.value || 100) * 0.01,
            audio_duration: parseFloat(document.getElementById('slider-acestep-duration')?.value || 20),
            shift: parseFloat(document.getElementById('slider-acestep-shift')?.value || 30) * 0.1,
            lm_temperature: parseFloat(document.getElementById('slider-acestep-temp')?.value || 85) * 0.01,
        };
    }

    // ------------------------------------------------------------------
    // API calls
    // ------------------------------------------------------------------
    async _checkStatus() {
        const statusEl = document.getElementById('acestep-status');
        const launchRow = document.getElementById('acestep-launch-row');
        try {
            const resp = await fetch(`${this.host}/jukebox/api/acestep/status`);
            const data = await resp.json();
            if (statusEl) {
                if (data.available) {
                    statusEl.textContent = `● Studio Online — ACE-Step V1.5 ready (${data.host})`;
                    statusEl.style.color = 'var(--jet-green)';
                    if (launchRow) launchRow.style.display = 'none';
                } else {
                    statusEl.textContent = `○ Studio Offline — ACE-Step not reachable at ${data.host}`;
                    statusEl.style.color = 'var(--jet-red)';
                    if (launchRow) launchRow.style.display = 'flex';
                }
            }
        } catch (e) {
            if (statusEl) {
                statusEl.textContent = '○ Studio Offline — Jukebox backend unreachable';
                statusEl.style.color = 'var(--jet-red)';
            }
        }
    }

    async _generate() {
        if (this._pending) return;
        this._pending = true;
        const resultEl = document.getElementById('acestep-result');
        if (resultEl) resultEl.textContent = 'Commissioning track...';

        try {
            // Save params
            const params = this._gatherParams();
            await fetch(`${this.host}/jukebox/api/acestep/params`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });

            // Trigger generation
            const resp = await fetch(`${this.host}/jukebox/api/acestep/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ caption: params.music_caption, lyrics: params.lyrics, duration: params.audio_duration })
            });
            const data = await resp.json();

            if (data.ok && data.audio_url) {
                if (resultEl) resultEl.textContent = `Track ready: ${data.audio_url.split('/').pop()}`;
                this._playAudio(data.audio_url);
            } else {
                if (resultEl) resultEl.textContent = 'Generation failed: ' + (data.error || 'unknown');
            }
        } catch (e) {
            if (resultEl) resultEl.textContent = 'Error: ' + String(e);
        } finally {
            this._pending = false;
        }
    }

    async _launchStudio() {
        const resultEl = document.getElementById('acestep-result');
        const launchBtn = document.getElementById('btn-acestep-launch');
        if (launchBtn) { launchBtn.disabled = true; launchBtn.textContent = 'Launching...'; }
        if (resultEl) resultEl.textContent = 'Installing & starting ACE-Step. This may take 2-5 minutes on first run...';
        try {
            const resp = await fetch(`${this.host}/jukebox/api/acestep/launch`, { method: 'POST' });
            const data = await resp.json();
            if (data.ok) {
                if (resultEl) resultEl.textContent = data.message;
                // Poll status every 5s for up to 5 min
                let attempts = 0;
                const poll = setInterval(async () => {
                    attempts++;
                    await this._checkStatus();
                    const statusEl = document.getElementById('acestep-status');
                    if (statusEl && statusEl.textContent.includes('Online')) {
                        clearInterval(poll);
                        if (resultEl) resultEl.textContent = 'ACE-Step is online!';
                        if (launchBtn) { launchBtn.disabled = false; launchBtn.textContent = 'Install & Launch ACE-Step Studio'; }
                    }
                    if (attempts > 60) {
                        clearInterval(poll);
                        if (resultEl) resultEl.textContent = 'Timed out waiting for ACE-Step. Check server logs.';
                        if (launchBtn) { launchBtn.disabled = false; launchBtn.textContent = 'Install & Launch ACE-Step Studio'; }
                    }
                }, 5000);
            } else {
                if (resultEl) resultEl.textContent = 'Launch failed: ' + (data.error || 'unknown');
                if (launchBtn) { launchBtn.disabled = false; launchBtn.textContent = 'Install & Launch ACE-Step Studio'; }
            }
        } catch (e) {
            if (resultEl) resultEl.textContent = 'Launch error: ' + String(e);
            if (launchBtn) { launchBtn.disabled = false; launchBtn.textContent = 'Install & Launch ACE-Step Studio'; }
        }
    }

    async _autoDJ() {
        const resultEl = document.getElementById('acestep-result');
        if (resultEl) resultEl.textContent = 'Auto-DJ selecting mood...';
        try {
            const resp = await fetch(`${this.host}/jukebox/api/acestep/auto_dj`, { method: 'POST' });
            const data = await resp.json();
            if (data.ok && data.audio_url) {
                if (resultEl) resultEl.textContent = `Auto-DJ: ${data.mood?.caption || 'track'} ready`;
                // Sync UI to returned mood params
                if (data.mood) {
                    const bpmSlider = document.getElementById('slider-acestep-bpm');
                    const bpmReadout = document.getElementById('val-acestep-bpm');
                    if (bpmSlider && data.mood.bpm) { bpmSlider.value = data.mood.bpm; bpmReadout.textContent = data.mood.bpm; }
                }
                this._playAudio(data.audio_url);
            } else {
                if (resultEl) resultEl.textContent = 'Auto-DJ failed: ' + (data.error || 'unknown');
            }
        } catch (e) {
            if (resultEl) resultEl.textContent = 'Auto-DJ error: ' + String(e);
        }
    }

    // ------------------------------------------------------------------
    // Audio playback + FFT → visualizer
    // ------------------------------------------------------------------
    _playAudio(url) {
        const player = document.getElementById('acestep-player');
        if (!player) return;

        player.src = url;
        player.style.display = 'block';
        player.crossOrigin = 'anonymous';
        player.play().catch(e => console.warn('[AceStep] Autoplay blocked:', e));

        // Wire Web Audio API analyser to feed the fluid engine
        this._ensureAudioContext();
        if (this._source) { try { this._source.disconnect(); } catch(e) {} }

        this._source = this._audioCtx.createMediaElementSource(player);
        this._source.connect(this._analyser);
        this._analyser.connect(this._gain);
        this._gain.connect(this._audioCtx.destination);

        // Start FFT loop
        this._startFFTLoop();
    }

    _ensureAudioContext() {
        if (!this._audioCtx) {
            this._audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            this._analyser = this._audioCtx.createAnalyser();
            this._analyser.fftSize = 512;
            this._analyser.smoothingTimeConstant = 0.8;
            this._gain = this._audioCtx.createGain();
            this._gain.gain.value = 0.8;
        }
        if (this._audioCtx.state === 'suspended') {
            this._audioCtx.resume();
        }
    }

    _startFFTLoop() {
        if (this._fftFrameId) cancelAnimationFrame(this._fftFrameId);

        const dataArray = new Uint8Array(this._analyser.frequencyBinCount);
        const loop = () => {
            this._analyser.getByteFrequencyData(dataArray);

            // Normalize to 0–1 floats
            const normalized = new Float32Array(dataArray.length);
            for (let i = 0; i < dataArray.length; i++) {
                normalized[i] = dataArray[i] / 255.0;
            }

            // Feed to fluid engine
            const fluid = window.jukeboxFluid;
            if (fluid && fluid.feedAudioFrame) {
                const frame = {
                    frequencyBins: normalized,
                    peak_amplitude: Math.max(...normalized),
                    zero_crossing_rate: 0,
                    spectral_centroid: 0.5,
                };
                fluid.feedAudioFrame(frame);
            }

            // Also update status overlay
            const status = document.getElementById('status');
            if (status && !status.classList.contains('live')) {
                status.textContent = '● Live — ACE-Step';
                status.classList.add('live');
            }

            this._fftFrameId = requestAnimationFrame(loop);
        };
        this._fftFrameId = requestAnimationFrame(loop);
    }
}

// Auto-initialize when DOM is ready
function initAceStepController() {
    window.acestepController = new AceStepController();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAceStepController);
} else {
    initAceStepController();
}
