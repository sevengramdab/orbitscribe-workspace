/**
 * Agent 4 — Main Breaker Engineering Dashboard (Fighter Jet Edition)
 * ==================================================================
 * Think of this file as the F-35 glass cockpit's central display
 * processor. It doesn't just read gauges — it directly manipulates
 * the engine throttles, nozzle vectors, and fuel mixture in real time.
 *
 * ELI5: This is like the pilot's HOTAS (Hands On Throttle And Stick)
 * system. Every slider twist immediately moves a control surface on
 * the actual aircraft — not just a remote request to ground control.
 */

class MainBreakerDashboard {
    constructor() {
        // ---- Panel references — like the MFD (Multi-Function Display) buttons ----
        this.panel = document.getElementById('dash-panel');
        this.toggleBtn = document.getElementById('dash-toggle');
        this.closeBtn = document.getElementById('dash-close');

        // ---- Breaker status elements — like the master caution annunciator ----
        this.led = document.getElementById('breaker-led');
        this.breakerLabel = document.getElementById('breaker-label');
        this.breakerReason = document.getElementById('breaker-reason');
        this.resetBtn = document.getElementById('breaker-reset');

        // ---- Slider references — like the throttle, nozzle, and mixture levers ----
        this.sliders = {
            viscosity: document.getElementById('slider-viscosity'),
            velocity: document.getElementById('slider-velocity'),
            frequency: document.getElementById('slider-frequency'),
            colortemp: document.getElementById('slider-colortemp'),
            bloom: document.getElementById('slider-bloom'),
            sunrays: document.getElementById('slider-sunrays'),
            dither: document.getElementById('slider-dither'),
            syllabic: document.getElementById('slider-syllabic'),
            negative: document.getElementById('slider-negative'),
            bpm: document.getElementById('slider-bpm'),
        };

        // ---- Readout references — like the HUD projected numbers on the canopy ----
        this.readouts = {
            viscosity: document.getElementById('val-viscosity'),
            velocity: document.getElementById('val-velocity'),
            frequency: document.getElementById('val-frequency'),
            colortemp: document.getElementById('val-colortemp'),
            bloom: document.getElementById('val-bloom'),
            sunrays: document.getElementById('val-sunrays'),
            dither: document.getElementById('val-dither'),
            syllabic: document.getElementById('val-syllabic'),
            negative: document.getElementById('val-negative'),
            bpm: document.getElementById('val-bpm'),
        };

        this.moodSelect = document.getElementById('select-mood');

        // ---- Telemetry — like the engine monitor on the right MFD ----
        this.fpsEl = document.getElementById('telemetry-fps');
        this.qualityEl = document.getElementById('telemetry-quality');

        this.gpuFills = [
            document.getElementById('gpu-0'),
            document.getElementById('gpu-1'),
            document.getElementById('gpu-2'),
            document.getElementById('gpu-3'),
            document.getElementById('gpu-4'),
        ];
        this.gpuPcts = [
            document.getElementById('gpu-0-pct'),
            document.getElementById('gpu-1-pct'),
            document.getElementById('gpu-2-pct'),
            document.getElementById('gpu-3-pct'),
            document.getElementById('gpu-4-pct'),
        ];

        this.sparkCanvas = document.getElementById('frame-sparkline');
        this.sparkCtx = this.sparkCanvas.getContext('2d');
        this.frameHistory = new Array(120).fill(16.67);

        this.debounceTimer = null;
        this.eventSource = null;
        this.statusInterval = null;
        this.lastFrameTime = performance.now();

        this._bindPanelToggle();
        this._bindSliders();
        this._bindMoodSelect();
        this._bindResetButton();
        this._startStatusPolling();
        this._startEventStream();
        this._startFrameLoop();
    }

    // ========================================================================
    // Panel open / close — like the MFD bezel buttons on a fighter jet
    // ========================================================================
    _bindPanelToggle() {
        this.toggleBtn.addEventListener('click', () => {
            this.panel.classList.add('open');
            this.toggleBtn.classList.add('active');
        });
        this.closeBtn.addEventListener('click', () => {
            this.panel.classList.remove('open');
            this.toggleBtn.classList.remove('active');
        });
        document.addEventListener('click', (e) => {
            const inside = this.panel.contains(e.target) || this.toggleBtn.contains(e.target);
            if (!inside && this.panel.classList.contains('open')) {
                this.panel.classList.remove('open');
                this.toggleBtn.classList.remove('active');
            }
        });
    }

    // ========================================================================
    // Slider bindings — DIRECT WIRING to front-end engines
    // ========================================================================
    _bindSliders() {
        const scales = {
            viscosity: { min: 0.0, max: 1.0, div: 100, fixed: 2 },
            velocity: { min: 0.5, max: 2.0, div: 100, fixed: 2 },
            frequency: { min: 0.0, max: 1.0, div: 100, fixed: 2 },
            colortemp: { min: 2000, max: 10000, div: 1, fixed: 0, suffix: ' K' },
            bloom: { min: 0.0, max: 1.0, div: 100, fixed: 2 },
            sunrays: { min: 0.0, max: 2.0, div: 100, fixed: 2 },
            dither: { min: 0.0, max: 0.1, div: 1000, fixed: 3 },
            syllabic: { min: 0.1, max: 1.0, div: 100, fixed: 2 },
            negative: { min: 0.0, max: 0.5, div: 100, fixed: 2 },
            bpm: { min: 60, max: 180, div: 1, fixed: 0 },
        };

        for (const [key, slider] of Object.entries(this.sliders)) {
            if (!slider) continue;

            // LIVE UPDATE: On every input tick, update the readout AND the engines
            slider.addEventListener('input', () => {
                const s = scales[key];
                const raw = parseFloat(slider.value);
                const scaled = s.min + (raw / s.div) * (s.max - s.min);
                const display = scaled.toFixed(s.fixed) + (s.suffix || '');
                this.readouts[key].textContent = display;

                // === FIGHTER JET DIRECT WIRING ===
                // Don't just fax a request to ground control —
                // move the control surface RIGHT NOW.
                this._applyLiveConfig(key, scaled);
            });

            // On release, debounce and sync to backend for persistence
            slider.addEventListener('change', () => {
                this._debouncedConfigUpdate();
            });
        }
    }

    // ========================================================================
    // LIVE CONFIG — Direct throttle to the engines (no backend round-trip)
    // ========================================================================
    _applyLiveConfig(key, value) {
        const fluid = window.jukeboxFluid;
        const audio = window.jukeboxAudio;
        if (!fluid && !audio) return;

        switch (key) {
            // ---- FLUID SIM CONTROLS ----
            case 'viscosity':
                if (fluid) fluid.applyConfig({ viscosity: value });
                break;
            case 'velocity':
                if (fluid) fluid.applyConfig({ flowVelocity: value });
                break;
            case 'frequency':
                // Frequency response scales splat radius
                if (fluid) fluid.applyConfig({ splatRadius: 0.001 + value * 0.008 });
                break;
            case 'colortemp':
                if (fluid) fluid.applyConfig({ colorTemp: value });
                break;
            case 'bloom':
                if (fluid) fluid.applyConfig({ bloomIntensity: value });
                break;
            case 'sunrays':
                if (fluid) fluid.applyConfig({ sunraysWeight: value });
                break;
            case 'dither':
                if (fluid) fluid.applyConfig({ ditherStrength: value });
                break;

            // ---- AUDIO ENGINE CONTROLS ----
            case 'syllabic':
                if (audio) audio.applyConfig({ maxSyllabicDensity: value });
                break;
            case 'negative':
                if (audio) audio.applyConfig({ minNegativeSpaceRatio: value });
                break;
            case 'bpm':
                if (audio) audio.applyConfig({ bpm: value });
                break;
        }
    }

    // ========================================================================
    // Mood preset — like switching between combat, cruise, and landing modes
    // ========================================================================
    _bindMoodSelect() {
        this.moodSelect.addEventListener('change', () => {
            const mood = this.moodSelect.value;
            const fluid = window.jukeboxFluid;
            const audio = window.jukeboxAudio;

            // Moods map to both audio palette and fluid color temperature
            const moodMap = {
                ambient:    { temp: 6500, bloom: 0.3, sunrays: 1.0, dither: 0.03 },
                energetic:  { temp: 4500, bloom: 0.6, sunrays: 1.5, dither: 0.02 },
                dark:       { temp: 2800, bloom: 0.15, sunrays: 0.3, dither: 0.05 },
                chaos:      { temp: 7500, bloom: 0.8, sunrays: 2.0, dither: 0.01 },
                minimal:    { temp: 9000, bloom: 0.1, sunrays: 0.0, dither: 0.08 },
            };
            const preset = moodMap[mood] || moodMap.ambient;

            if (fluid) {
                fluid.applyConfig({
                    colorTemp: preset.temp,
                    bloomIntensity: preset.bloom,
                    sunraysWeight: preset.sunrays,
                    ditherStrength: preset.dither,
                });
            }
            if (audio) {
                audio.applyConfig({ mood });
            }

            // Sync sliders to match preset
            this._syncSlider('colortemp', preset.temp, 2000, 10000);
            this._syncSlider('bloom', preset.bloom, 0, 1);
            this._syncSlider('sunrays', preset.sunrays, 0, 2);
            this._syncSlider('dither', preset.dither, 0, 0.1);

            this._debouncedConfigUpdate();
        });
    }

    _syncSlider(key, value, min, max) {
        const slider = this.sliders[key];
        const readout = this.readouts[key];
        if (!slider) return;
        const scales = {
            colortemp: { div: 1, fixed: 0, suffix: ' K' },
            bloom: { div: 100, fixed: 2 },
            sunrays: { div: 100, fixed: 2 },
            dither: { div: 1000, fixed: 3 },
        };
        const s = scales[key];
        const pct = (value - min) / (max - min);
        slider.value = Math.round(pct * s.div);
        readout.textContent = value.toFixed(s.fixed) + (s.suffix || '');
    }

    // ========================================================================
    // Reset button — like the FIRE TEST / MASTER CAUTION reset
    // ========================================================================
    _bindResetButton() {
        this.resetBtn.addEventListener('click', async () => {
            this.resetBtn.disabled = true;
            try {
                const resp = await fetch('/jukebox/api/breaker/reset', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                if (!resp.ok) throw new Error(`Breaker reset failed: ${resp.status}`);
                // Also reset frontend lock state
                const audio = window.jukeboxAudio;
                if (audio) audio.applyConfig({ lockState: 'free' });
            } catch (err) {
                console.error('[Dashboard] Breaker reset error:', err);
            } finally {
                setTimeout(() => { this.resetBtn.disabled = false; }, 1500);
            }
        });
    }

    // ========================================================================
    // Debounced backend sync — like the black-box recorder that logs settings
    // ========================================================================
    _debouncedConfigUpdate() {
        if (this.debounceTimer) clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this._sendConfig();
        }, 200);
    }

    async _sendConfig() {
        const payload = {
            viscosity: parseFloat(this.sliders.viscosity.value) / 100,
            flowVelocity: 0.5 + (parseFloat(this.sliders.velocity.value) / 100) * 1.5,
            frequencyResponse: parseFloat(this.sliders.frequency.value) / 100,
            colorTemp: parseInt(this.sliders.colortemp.value, 10),
            bloomIntensity: parseFloat(this.sliders.bloom.value) / 100,
            sunraysWeight: parseFloat(this.sliders.sunrays.value) / 100 * 2.0,
            ditherStrength: parseFloat(this.sliders.dither.value) / 1000,
            maxSyllabicDensity: 0.1 + (parseFloat(this.sliders.syllabic.value) / 100) * 0.9,
            minNegativeSpaceRatio: parseFloat(this.sliders.negative.value) / 100 * 0.5,
            bpm: parseInt(this.sliders.bpm.value, 10),
            mood: this.moodSelect.value,
        };

        try {
            const resp = await fetch('/jukebox/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!resp.ok) throw new Error(`Config POST failed: ${resp.status}`);
        } catch (err) {
            console.error('[Dashboard] Config update error:', err);
        }
    }

    // ========================================================================
    // Status polling — like the engine monitor scanning every 500 ms
    // ========================================================================
    _startStatusPolling() {
        this.statusInterval = setInterval(async () => {
            try {
                const resp = await fetch('/jukebox/api/status');
                if (!resp.ok) return;
                const data = await resp.json();
                this._updateBreakerStatus(data);
            } catch (err) {}
        }, 500);
    }

    // ========================================================================
    // SSE stream — like the MIL-STD-1553 data bus
    // ========================================================================
    _startEventStream() {
        try {
            this.eventSource = new EventSource('/jukebox/api/stream');
            this.eventSource.addEventListener('open', () => {
                console.log('[Dashboard] SSE bus connected.');
            });
            this.eventSource.addEventListener('message', (e) => {
                try {
                    const data = JSON.parse(e.data);
                    this._handleStreamData(data);
                } catch (parseErr) {
                    console.error('[Dashboard] SSE parse error:', parseErr);
                }
            });
            this.eventSource.addEventListener('error', () => {
                this.eventSource.close();
                this.eventSource = null;
                setTimeout(() => this._startEventStream(), 5000);
            });
        } catch (err) {
            console.error('[Dashboard] SSE init error:', err);
        }
    }

    // ========================================================================
    // Breaker annunciator — like the master caution panel
    // ========================================================================
    _updateBreakerStatus(data) {
        const status = (data.breaker_lock_state || 'free').toLowerCase();
        this.led.classList.remove('green', 'yellow', 'red');

        if (status === 'free' || status === 'normal') {
            this.led.classList.add('green');
            this.breakerLabel.textContent = 'NORM';
            this.breakerLabel.style.color = 'var(--success)';
        } else if (status === 'locked') {
            this.led.classList.add('yellow');
            this.breakerLabel.textContent = 'WARN';
            this.breakerLabel.style.color = 'var(--warning)';
        } else {
            this.led.classList.add('red');
            this.breakerLabel.textContent = 'OVERRIDE';
            this.breakerLabel.style.color = 'var(--danger)';
        }

        const reason = data.breaker_reason || '';
        this.breakerReason.textContent = reason;
    }

    // ========================================================================
    // Telemetry stream — like the right MFD engine display
    // ========================================================================
    _handleStreamData(data) {
        if (Array.isArray(data.gpu_utilization)) {
            data.gpu_utilization.forEach((pct, idx) => {
                if (idx >= this.gpuFills.length) return;
                const clamped = Math.max(0, Math.min(100, pct));
                this.gpuFills[idx].style.width = `${clamped}%`;
                this.gpuPcts[idx].textContent = `${Math.round(clamped)}%`;
            });
        }

        if (typeof data.frame_time_ms === 'number') {
            this.frameHistory.push(data.frame_time_ms);
            this.frameHistory.shift();
        }

        if (typeof data.fps === 'number') {
            this.fpsEl.textContent = Math.round(data.fps);
        }

        if (data.quality_level) {
            this.qualityEl.innerHTML = `<span class="quality-badge">${data.quality_level.toUpperCase()}</span>`;
        }
    }

    // ========================================================================
    // Frame loop — like the HUD refresh sync
    // ========================================================================
    _startFrameLoop() {
        const tick = () => {
            this._measureFrameTime();
            this._drawSparkline();
            requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    }

    _measureFrameTime() {
        const now = performance.now();
        const delta = now - this.lastFrameTime;
        this.lastFrameTime = now;
        if (delta > 0 && delta < 200) {
            this.frameHistory.push(delta);
            this.frameHistory.shift();
        }
    }

    _drawSparkline() {
        const ctx = this.sparkCtx;
        const w = this.sparkCanvas.width;
        const h = this.sparkCanvas.height;
        ctx.clearRect(0, 0, w, h);
        if (this.frameHistory.length < 2) return;

        const maxVal = Math.max(...this.frameHistory, 33.33);
        const range = maxVal || 1;

        ctx.strokeStyle = 'rgba(0, 229, 255, 0.85)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        for (let i = 0; i < this.frameHistory.length; i++) {
            const x = (i / (this.frameHistory.length - 1)) * w;
            const y = (1 - (this.frameHistory[i] / range)) * (h - 4) + 2;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();

        const refY = (1 - (16.67 / range)) * (h - 4) + 2;
        if (refY > 0 && refY < h) {
            ctx.strokeStyle = 'rgba(0, 229, 255, 0.15)';
            ctx.lineWidth = 1;
            ctx.setLineDash([3, 3]);
            ctx.beginPath();
            ctx.moveTo(0, refY);
            ctx.lineTo(w, refY);
            ctx.stroke();
            ctx.setLineDash([]);
        }
    }

    destroy() {
        if (this.statusInterval) clearInterval(this.statusInterval);
        if (this.eventSource) this.eventSource.close();
        if (this.debounceTimer) clearTimeout(this.debounceTimer);
    }
}

// Bootstrap
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.mainBreakerDashboard = new MainBreakerDashboard();
    });
} else {
    window.mainBreakerDashboard = new MainBreakerDashboard();
}
