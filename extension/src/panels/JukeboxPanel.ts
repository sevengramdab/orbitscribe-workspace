import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export class JukeboxPanel {
    public static currentPanel: JukeboxPanel | undefined;
    public static readonly viewType = 'orbitscribe.jukeboxPanel';
    private readonly _panel: vscode.WebviewPanel;

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.ViewColumn.Beside;
        if (JukeboxPanel.currentPanel) {
            JukeboxPanel.currentPanel._panel.reveal(column);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            JukeboxPanel.viewType,
            'Infinite Jukebox',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri],
            }
        );
        JukeboxPanel.currentPanel = new JukeboxPanel(panel, extensionUri);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._panel.webview.html = this._buildHtml(extensionUri);
        this._panel.onDidDispose(() => { JukeboxPanel.currentPanel = undefined; });
        this._panel.webview.onDidReceiveMessage(async (msg) => {
            switch (msg.command) {
                case 'openBrowser':
                    vscode.env.openExternal(vscode.Uri.parse('http://127.0.0.1:58080/jukebox/'));
                    break;
                case 'openBrowser8503':
                    vscode.env.openExternal(vscode.Uri.parse('http://127.0.0.1:8503'));
                    break;
                case 'generate':
                    try {
                        const resp = await fetch('http://127.0.0.1:58080/jukebox/api/generate', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ lyrics: msg.lyrics, tags: msg.tags, duration: msg.duration })
                        });
                        const data: any = await resp.json();
                        this._panel.webview.postMessage({ command: 'generated', ok: data.ok, backend: data.backend });
                    } catch (e) {
                        this._panel.webview.postMessage({ command: 'generated', ok: false, error: String(e) });
                    }
                    break;
                case 'checkStatus':
                    try {
                        const resp = await fetch('http://127.0.0.1:58080/jukebox/api/status');
                        const data = await resp.json();
                        this._panel.webview.postMessage({ command: 'statusUpdate', data });
                    } catch (e) {
                        this._panel.webview.postMessage({ command: 'statusUpdate', data: { running: false } });
                    }
                    break;
                case 'launchWebUI':
                    try {
                        const resp = await fetch('http://127.0.0.1:58080/jukebox/api/auto_dj/launch', { method: 'POST' });
                        const data = await resp.json();
                        this._panel.webview.postMessage({ command: 'webuiLaunched', data });
                    } catch (e) {
                        this._panel.webview.postMessage({ command: 'webuiLaunched', data: { ok: false, error: String(e) } });
                    }
                    break;
                case 'killAutoDJ':
                    try {
                        const resp = await fetch('http://127.0.0.1:58080/jukebox/api/auto_dj/kill', { method: 'POST' });
                        const data = await resp.json();
                        this._panel.webview.postMessage({ command: 'autoDJKilled', data });
                    } catch (e) {
                        this._panel.webview.postMessage({ command: 'autoDJKilled', data: { ok: false, error: String(e) } });
                    }
                    break;
                case 'optimizeSystem':
                    try {
                        const resp = await fetch('http://127.0.0.1:58080/jukebox/api/system/optimize', { method: 'POST' });
                        const data = await resp.json();
                        this._panel.webview.postMessage({ command: 'systemOptimized', data });
                    } catch (e) {
                        this._panel.webview.postMessage({ command: 'systemOptimized', data: { ok: false, error: String(e) } });
                    }
                    break;
                case 'fetchHardware':
                    try {
                        const resp = await fetch('http://127.0.0.1:58080/jukebox/api/hardware');
                        const data = await resp.json();
                        this._panel.webview.postMessage({ command: 'hardwareUpdate', data });
                    } catch (e) {
                        this._panel.webview.postMessage({ command: 'hardwareUpdate', data: null });
                    }
                    break;
                case 'fetchAutoDJStatus':
                    try {
                        const resp = await fetch('http://127.0.0.1:58080/jukebox/api/auto_dj/status');
                        const data = await resp.json();
                        this._panel.webview.postMessage({ command: 'autoDJStatusUpdate', data });
                    } catch (e) {
                        this._panel.webview.postMessage({ command: 'autoDJStatusUpdate', data: null });
                    }
                    break;
            }
        });
    }

    public reveal() {
        this._panel.reveal(vscode.ViewColumn.Beside);
    }

    public sendMessage(msg: any) {
        this._panel.webview.postMessage(msg);
    }

    private _buildHtml(extensionUri: vscode.Uri): string {
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
            ?? path.join(extensionUri.fsPath, '..');
        let jukeboxJs = '';
        let audioEngineJs = '';
        let dashboardJs = '';
        let themesJs = '';
        let acestepJs = '';
        const tryPaths = [
            path.join(workspaceRoot, 'infinite_jukebox', 'static'),
            path.join(extensionUri.fsPath, 'media', 'jukebox'),
        ];
        for (const dir of tryPaths) {
            if (jukeboxJs && audioEngineJs && dashboardJs && themesJs) break;
            try {
                const jbPath = path.join(dir, 'jukebox.js');
                const aePath = path.join(dir, 'audio_engine.js');
                const dbPath = path.join(dir, 'dashboard.js');
                const thPath = path.join(dir, 'themes.js');
                if (!jukeboxJs && fs.existsSync(jbPath)) jukeboxJs = fs.readFileSync(jbPath, 'utf-8');
                if (!audioEngineJs && fs.existsSync(aePath)) audioEngineJs = fs.readFileSync(aePath, 'utf-8');
                if (!dashboardJs && fs.existsSync(dbPath)) dashboardJs = fs.readFileSync(dbPath, 'utf-8');
                if (!themesJs && fs.existsSync(thPath)) themesJs = fs.readFileSync(thPath, 'utf-8');
                const asPath = path.join(dir, 'acestep.js');
                if (!acestepJs && fs.existsSync(asPath)) acestepJs = fs.readFileSync(asPath, 'utf-8');
            } catch { /* ignore */ }
        }
        const loadedReal = !!(jukeboxJs && audioEngineJs);
        if (!jukeboxJs) jukeboxJs = this._minimalJukeboxJs();
        if (!audioEngineJs) audioEngineJs = this._minimalAudioJs();
        if (!dashboardJs) dashboardJs = this._minimalDashboardJs();

        return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline' 'unsafe-eval'; connect-src http://127.0.0.1:* http://127.0.0.1:7860; img-src blob: data:; media-src http://127.0.0.1:* http://127.0.0.1:7860;">
<title>Infinite Jukebox</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;500;700&display=swap');
:root{--jet-bg:#06080a;--jet-panel:rgba(8,12,16,0.94);--jet-panel-border:rgba(0,229,255,0.18);--jet-cyan:#00e5ff;--jet-cyan-dim:rgba(0,229,255,0.25);--jet-cyan-glow:rgba(0,229,255,0.55);--jet-amber:#ff9500;--jet-amber-dim:rgba(255,149,0,0.3);--jet-red:#ff2a2a;--jet-red-dim:rgba(255,42,42,0.3);--jet-green:#39ff14;--jet-green-dim:rgba(57,255,20,0.3);--jet-text:#c8e6e6;--jet-muted:#5a7a7a;--jet-font:'Orbitron','Segoe UI',system-ui,sans-serif;--jet-mono:'Share Tech Mono','Consolas',monospace;}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%;height:100%;background:var(--jet-bg);color:var(--jet-text);font-family:var(--jet-font);overflow:hidden;font-size:14px}
#fluid-canvas{position:fixed;inset:0;width:100vw;height:100vh;display:block;z-index:0;background:radial-gradient(ellipse at center,#0c1018 0%,#020408 100%)}
.scanlines{position:fixed;inset:0;z-index:2;pointer-events:none;background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.12) 2px,rgba(0,0,0,0.12) 4px);opacity:0.35}
.vignette{position:fixed;inset:0;z-index:3;pointer-events:none;background:radial-gradient(ellipse at center,transparent 60%,rgba(0,0,0,0.5) 100%)}
.hud{position:fixed;z-index:10;pointer-events:none}
.hud-top-left{top:1.25rem;left:1.5rem}
.hud-top-right{top:1.25rem;right:1.5rem;text-align:right}
.hud-bottom-center{bottom:2.5rem;left:50%;transform:translateX(-50%);pointer-events:auto}
.brand{font-size:0.65rem;letter-spacing:0.35em;text-transform:uppercase;color:var(--jet-cyan);text-shadow:0 0 6px var(--jet-cyan-dim);font-family:var(--jet-font);font-weight:500}
.brand::before{content:'▶ ';color:var(--jet-green);text-shadow:0 0 8px var(--jet-green)}
.title{font-size:1.6rem;font-weight:700;margin-top:0.2rem;letter-spacing:0.08em;text-transform:uppercase;color:var(--jet-text);text-shadow:0 0 12px rgba(200,230,230,0.15);font-family:var(--jet-font)}
.status-pill{display:inline-block;padding:0.3rem 0.8rem;background:var(--jet-panel);border:1px solid var(--jet-panel-border);font-size:0.75rem;color:var(--jet-muted);font-family:var(--jet-mono);letter-spacing:0.08em;clip-path:polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px)}
.status-pill.live{color:var(--jet-green);border-color:var(--jet-green);box-shadow:0 0 10px var(--jet-green-dim),inset 0 0 6px var(--jet-green-dim);animation:hud-pulse 2s ease-in-out infinite}
@keyframes hud-pulse{0%,100%{box-shadow:0 0 10px var(--jet-green-dim),inset 0 0 6px var(--jet-green-dim)}50%{box-shadow:0 0 18px var(--jet-green),inset 0 0 10px var(--jet-green-dim)}}
.dashboard-toggle{position:fixed;top:1.25rem;right:1.25rem;z-index:110;background:var(--jet-panel);border:1px solid var(--jet-panel-border);color:var(--jet-cyan);width:2.75rem;height:2.75rem;clip-path:polygon(6px 0,100% 0,100% calc(100% - 6px),calc(100% - 6px) 100%,0 100%,0 6px);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:1.1rem;transition:all 0.25s ease;font-family:var(--jet-font)}
.dashboard-toggle:hover,.dashboard-toggle.active{border-color:var(--jet-cyan);box-shadow:0 0 14px var(--jet-cyan-dim),inset 0 0 8px var(--jet-cyan-dim);color:var(--jet-cyan);text-shadow:0 0 10px var(--jet-cyan-glow)}
.dashboard-panel{position:fixed;top:0;right:0;width:420px;max-width:92vw;height:100vh;z-index:105;background:var(--jet-panel);border-left:1px solid var(--jet-panel-border);backdrop-filter:blur(16px);transform:translateX(100%);transition:transform 0.3s cubic-bezier(0.4,0,0.2,1);display:flex;flex-direction:column;overflow:hidden;box-shadow:-8px 0 32px rgba(0,0,0,0.5)}
.dashboard-panel.open{transform:translateX(0)}
.dashboard-header{padding:1rem 1.25rem;border-bottom:1px solid var(--jet-panel-border);display:flex;align-items:center;justify-content:space-between;background:linear-gradient(90deg,rgba(0,229,255,0.04),transparent)}
.dashboard-header h2{font-size:0.8rem;letter-spacing:0.2em;text-transform:uppercase;color:var(--jet-cyan);font-weight:700;font-family:var(--jet-font);text-shadow:0 0 6px var(--jet-cyan-dim)}
.dashboard-close{background:none;border:none;color:var(--jet-muted);font-size:1.3rem;cursor:pointer;transition:color 0.2s;font-family:var(--jet-font)}
.dashboard-close:hover{color:var(--jet-cyan);text-shadow:0 0 8px var(--jet-cyan-dim)}
.dashboard-body{flex:1;overflow-y:auto;padding:1rem 1.25rem;display:flex;flex-direction:column;gap:1rem}
.dashboard-body::-webkit-scrollbar{width:3px}
.dashboard-body::-webkit-scrollbar-track{background:transparent}
.dashboard-body::-webkit-scrollbar-thumb{background:var(--jet-cyan-dim);border-radius:2px}
.dash-section{background:rgba(6,10,14,0.7);border:1px solid var(--jet-panel-border);padding:1rem;position:relative}
.dash-section::before{content:'';position:absolute;top:-1px;left:0;width:40px;height:2px;background:var(--jet-cyan);box-shadow:0 0 8px var(--jet-cyan-dim)}
.dash-section-title{font-size:0.65rem;letter-spacing:0.18em;text-transform:uppercase;color:var(--jet-muted);margin-bottom:0.75rem;font-weight:700;font-family:var(--jet-font);display:flex;align-items:center;gap:0.5rem}
.dash-section-title::before{content:'';display:inline-block;width:4px;height:4px;background:var(--jet-cyan);box-shadow:0 0 6px var(--jet-cyan)}
.breaker-status{display:flex;align-items:center;gap:0.875rem;margin-bottom:0.75rem}
.breaker-led{width:16px;height:16px;background:var(--jet-muted);border:2px solid rgba(255,255,255,0.06);box-shadow:inset 0 1px 2px rgba(0,0,0,0.5);transition:all 0.3s ease;flex-shrink:0;clip-path:polygon(30% 0,70% 0,100% 30%,100% 70%,70% 100%,30% 100%,0 70%,0 30%)}
.breaker-led.green{background:var(--jet-green);box-shadow:0 0 14px var(--jet-green),inset 0 1px 2px rgba(0,0,0,0.3)}
.breaker-led.yellow{background:var(--jet-amber);box-shadow:0 0 14px var(--jet-amber),inset 0 1px 2px rgba(0,0,0,0.3);animation:led-blink 1s ease-in-out infinite}
.breaker-led.red{background:var(--jet-red);box-shadow:0 0 18px var(--jet-red),inset 0 1px 2px rgba(0,0,0,0.3);animation:led-blink 0.6s ease-in-out infinite}
@keyframes led-blink{0%,100%{opacity:1}50%{opacity:0.4}}
.breaker-label{font-family:var(--jet-mono);font-size:0.85rem;color:var(--jet-text);letter-spacing:0.1em;font-weight:700}
.breaker-reason{font-family:var(--jet-mono);font-size:0.7rem;color:var(--jet-red);margin-bottom:0.75rem;min-height:1.2em;text-shadow:0 0 4px var(--jet-red-dim)}
.breaker-reset{width:100%;padding:0.5rem 0;background:rgba(255,42,42,0.08);border:1px solid rgba(255,42,42,0.35);color:var(--jet-red);font-family:var(--jet-font);font-size:0.7rem;letter-spacing:0.15em;text-transform:uppercase;cursor:pointer;clip-path:polygon(6px 0,100% 0,100% calc(100% - 6px),calc(100% - 6px) 100%,0 100%,0 6px);transition:all 0.2s ease;font-weight:500}
.breaker-reset:hover{background:rgba(255,42,42,0.2);border-color:var(--jet-red);box-shadow:0 0 14px var(--jet-red-dim),inset 0 0 8px var(--jet-red-dim);text-shadow:0 0 8px var(--jet-red)}
.breaker-reset:disabled{opacity:0.3;cursor:not-allowed}
.control-row{display:flex;flex-direction:column;gap:0.3rem;margin-bottom:0.55rem}
.control-row:last-child{margin-bottom:0}
.control-label{display:flex;justify-content:space-between;font-size:0.68rem;color:var(--jet-muted);font-family:var(--jet-font);letter-spacing:0.05em}
.control-value{font-family:var(--jet-mono);color:var(--jet-cyan);font-size:0.72rem;text-shadow:0 0 4px var(--jet-cyan-dim)}
input[type="range"]{-webkit-appearance:none;appearance:none;width:100%;height:3px;background:rgba(255,255,255,0.05);border-radius:0;outline:none;cursor:pointer;position:relative}
input[type="range"]::-webkit-slider-thumb{-webkit-appearance:none;appearance:none;width:12px;height:12px;background:var(--jet-cyan);clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%);box-shadow:0 0 10px var(--jet-cyan-glow);cursor:pointer;transition:box-shadow 0.2s,transform 0.15s;margin-top:-4.5px}
input[type="range"]::-webkit-slider-thumb:hover{box-shadow:0 0 18px var(--jet-cyan);transform:scale(1.2)}
input[type="range"]::-moz-range-thumb{width:12px;height:12px;background:var(--jet-cyan);clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%);box-shadow:0 0 10px var(--jet-cyan-glow);cursor:pointer;border:none}
select.dash-select{width:100%;padding:0.4rem 0.6rem;background:rgba(6,10,14,0.8);border:1px solid var(--jet-panel-border);color:var(--jet-text);font-family:var(--jet-font);font-size:0.75rem;cursor:pointer;outline:none;transition:border-color 0.2s;clip-path:polygon(4px 0,100% 0,100% calc(100% - 4px),calc(100% - 4px) 100%,0 100%,0 4px)}
select.dash-select:focus{border-color:var(--jet-cyan);box-shadow:0 0 8px var(--jet-cyan-dim)}
.telemetry-grid{display:grid;grid-template-columns:1fr 1fr;gap:0.5rem}
.telemetry-item{background:rgba(6,10,14,0.5);border:1px solid var(--jet-panel-border);padding:0.45rem 0.55rem;position:relative}
.telemetry-item.wide{grid-column:1/-1}
.telemetry-label{font-size:0.6rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--jet-muted);font-family:var(--jet-font);margin-bottom:0.2rem}
.telemetry-value{font-family:var(--jet-mono);font-size:0.95rem;color:var(--jet-cyan);text-shadow:0 0 6px var(--jet-cyan-dim)}
.telemetry-value.dim{color:var(--jet-muted)}
.gpu-list{display:flex;flex-direction:column;gap:0.4rem}
.gpu-row{display:flex;align-items:center;gap:0.5rem}
.gpu-name{font-family:var(--jet-mono);font-size:0.62rem;color:var(--jet-muted);width:3rem;flex-shrink:0;text-align:right}
.gpu-track{flex:1;height:5px;background:rgba(255,255,255,0.03);overflow:hidden;position:relative}
.gpu-fill{height:100%;width:0%;background:linear-gradient(90deg,var(--jet-cyan-dim),var(--jet-cyan));box-shadow:0 0 6px var(--jet-cyan-dim);transition:width 0.4s ease}
.gpu-pct{font-family:var(--jet-mono);font-size:0.62rem;color:var(--jet-muted);width:2.2rem;text-align:right;flex-shrink:0}
.sparkline-wrap{width:100%;height:40px;background:rgba(6,10,14,0.5);border:1px solid var(--jet-panel-border);overflow:hidden}
#frame-sparkline{display:block;width:100%;height:100%}
.quality-badge{display:inline-block;padding:0.15rem 0.4rem;font-family:var(--jet-mono);font-size:0.65rem;background:rgba(0,229,255,0.06);border:1px solid var(--jet-panel-border);color:var(--jet-cyan);letter-spacing:0.05em}
.loader{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;z-index:100;background:var(--jet-bg);transition:opacity 0.5s ease}
.loader.hidden{opacity:0;pointer-events:none}
.spinner{width:40px;height:40px;border:2px solid rgba(0,229,255,0.1);border-top-color:var(--jet-cyan);clip-path:polygon(30% 0,70% 0,100% 30%,100% 70%,70% 100%,30% 100%,0 70%,0 30%);animation:spin 0.8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.auto-dj-row{display:flex;gap:0.5rem;margin-bottom:0.5rem}
.auto-dj-row .breaker-reset{flex:1}
.auto-dj-status-msg{margin-top:0.5rem;font-family:var(--jet-mono);font-size:0.65rem;color:var(--jet-muted);min-height:1.2em}
.track-meta-overlay{position:fixed;bottom:5rem;left:1.5rem;z-index:10;pointer-events:none;opacity:0;transition:opacity 0.5s ease}
.track-meta-overlay.visible{opacity:1}
.track-meta-line{font-family:var(--jet-mono);font-size:0.7rem;color:var(--jet-muted);letter-spacing:0.05em}
.track-meta-line .highlight{color:var(--jet-cyan);text-shadow:0 0 6px var(--jet-cyan-dim)}
.track-title{color:var(--jet-amber);text-shadow:0 0 6px var(--jet-amber-dim);font-size:0.8rem;margin-top:0.2rem}
@media(max-width:640px){.title{font-size:1.2rem}.hud-top-right{display:none}.dashboard-panel{width:100vw}.track-meta-overlay{bottom:7rem}}
</style>
</head>
<body>
<div class="scanlines"></div>
<div class="vignette"></div>
<div id="loader" class="loader"><div class="spinner"></div></div>
<canvas id="fluid-canvas"></canvas><canvas id="particle-canvas" style="position:fixed;inset:0;width:100vw;height:100vh;z-index:1;pointer-events:none;display:block;"></canvas>
<div class="hud hud-top-left">
<div class="brand">OrbitScribe Labs</div>
<div class="title">Infinite Jukebox</div>
<div id="track-meta" style="margin-top:0.4rem;font-size:0.65rem;color:var(--jet-muted);font-family:var(--jet-mono);opacity:0;transition:opacity 0.5s ease;">
<span id="meta-bpm">---</span> BPM · <span id="meta-key">---</span> · <span id="meta-ts">---</span><br>
<span id="meta-title" style="color:var(--jet-cyan);text-shadow:0 0 4px var(--jet-cyan-dim);"></span>
</div>
</div>
<div class="hud hud-top-right"><div id="status" class="status-pill">INITIALIZING</div><div id="gpu-badge" style="margin-top:0.4rem;font-size:0.65rem;color:var(--jet-muted);font-family:var(--jet-mono);"></div></div>
<div class="track-meta-overlay" id="track-overlay"><div class="track-meta-line">AUTO DJ <span class="highlight" id="overlay-bpm">---</span> BPM · <span class="highlight" id="overlay-key">---</span> · <span class="highlight" id="overlay-ts">---</span></div><div class="track-title" id="overlay-title"></div></div>
<button id="dash-toggle" class="dashboard-toggle" aria-label="Open Dashboard" title="Engineering Dashboard">&#9889;</button>
<aside id="dash-panel" class="dashboard-panel">
<div class="dashboard-header"><h2>Main Breaker</h2><button id="dash-close" class="dashboard-close" aria-label="Close Dashboard">&times;</button></div>
<div class="dashboard-body">
<div class="dash-section">
<div class="dash-section-title">Breaker Status</div>
<div class="breaker-status"><div id="breaker-led" class="breaker-led green"></div><div id="breaker-label" class="breaker-label">NORM</div></div>
<div id="breaker-reason" class="breaker-reason"></div>
<button id="breaker-reset" class="breaker-reset">Reset Breaker</button>
</div>
<div class="dash-section">
<div class="dash-section-title">AUTO DJ Control</div>
<div class="auto-dj-row">
<button id="btn-launch-webui" class="breaker-reset" style="border-color:var(--jet-cyan);color:var(--jet-cyan);">Launch Web UI</button>
<button id="btn-kill-autodj" class="breaker-reset">Kill All</button>
</div>
<button id="btn-optimize" class="breaker-reset" style="border-color:var(--jet-green);color:var(--jet-green);">Optimize System</button>
<div id="auto-dj-status" class="auto-dj-status-msg"></div>
</div>
<div class="dash-section">
<div class="dash-section-title">Hardware Profile</div>
<div class="telemetry-grid">
<div class="telemetry-item"><div class="telemetry-label">GPU</div><div id="hw-gpu" class="telemetry-value dim">---</div></div>
<div class="telemetry-item"><div class="telemetry-label">VRAM</div><div id="hw-vram" class="telemetry-value dim">---</div></div>
<div class="telemetry-item"><div class="telemetry-label">CPU</div><div id="hw-cpu" class="telemetry-value dim">---</div></div>
<div class="telemetry-item"><div class="telemetry-label">RAM</div><div id="hw-ram" class="telemetry-value dim">---</div></div>
</div>
<div style="margin-top:0.5rem;text-align:center;"><span id="hw-tier" class="quality-badge">---</span></div>
</div>
<div class="dash-section">
<div class="dash-section-title">Visualizer Settings</div>
<div class="control-row"><div class="control-label"><span>Fluid Viscosity</span><span id="val-viscosity" class="control-value">0.50</span></div><input type="range" id="slider-viscosity" min="0" max="100" value="50"></div>
<div class="control-row"><div class="control-label"><span>Flow Velocity</span><span id="val-velocity" class="control-value">1.25</span></div><input type="range" id="slider-velocity" min="50" max="200" value="125"></div>
<div class="control-row"><div class="control-label"><span>Frequency Response</span><span id="val-frequency" class="control-value">0.50</span></div><input type="range" id="slider-frequency" min="0" max="100" value="50"></div>
<div class="control-row"><div class="control-label"><span>Color Temperature</span><span id="val-colortemp" class="control-value">5500 K</span></div><input type="range" id="slider-colortemp" min="2000" max="10000" value="5500" step="100"></div>
<div class="control-row"><div class="control-label"><span>Bloom Intensity</span><span id="val-bloom" class="control-value">0.50</span></div><input type="range" id="slider-bloom" min="0" max="100" value="50"></div>
<div class="control-row"><div class="control-label"><span>Sunrays Weight</span><span id="val-sunrays" class="control-value">1.00</span></div><input type="range" id="slider-sunrays" min="0" max="200" value="100"></div>
<div class="control-row"><div class="control-label"><span>Dither Strength</span><span id="val-dither" class="control-value">0.05</span></div><input type="range" id="slider-dither" min="0" max="10" value="5"></div>
</div>
<div class="dash-section">
<div class="dash-section-title">Audio Settings</div>
<div class="control-row"><div class="control-label"><span>ACE Step 1.5 Max Density</span><span id="val-syllabic" class="control-value">0.55</span></div><input type="range" id="slider-syllabic" min="10" max="100" value="55"></div>
<div class="control-row"><div class="control-label"><span>Negative Space Ratio</span><span id="val-negative" class="control-value">0.25</span></div><input type="range" id="slider-negative" min="0" max="50" value="25"></div>
<div class="control-row"><div class="control-label"><span>Tempo BPM</span><span id="val-bpm" class="control-value">110</span></div><input type="range" id="slider-bpm" min="60" max="180" value="110"></div>
<div class="control-row"><div class="control-label"><span>Mood Preset</span></div><select id="select-mood" class="dash-select"><option value="ambient">Ambient</option><option value="energetic">Energetic</option><option value="dark">Dark</option><option value="chaos">Chaos</option><option value="minimal">Minimal</option></select></div><div class="control-row"><div class="control-label"><span>Visualizer Theme</span></div><select id="select-theme" class="dash-select"><option value="aurora">Aurora (Bright)</option><option value="nebula">Nebula (Cosmic)</option><option value="inferno">Inferno (Fire)</option><option value="ocean">Ocean (Deep)</option><option value="matrix">Matrix (Digital)</option><option value="dark">Dark (Classic)</option></select></div>
</div>
<div class="dash-section">
<div class="dash-section-title">Hardware Telemetry</div>
<div class="telemetry-grid">
<div class="telemetry-item"><div class="telemetry-label">FPS</div><div id="telemetry-fps" class="telemetry-value">0</div></div>
<div class="telemetry-item"><div class="telemetry-label">Quality</div><div id="telemetry-quality" class="telemetry-value"><span class="quality-badge">AUTO</span></div></div>
<div class="telemetry-item wide"><div class="telemetry-label">GPU Utilization</div><div class="gpu-list" id="gpu-list"></div></div>
<div class="telemetry-item wide"><div class="telemetry-label">Frame Time (ms)</div><div class="sparkline-wrap"><canvas id="frame-sparkline" width="320" height="40"></canvas></div></div>
</div>
</div>
</div>
</aside>
<script>
const vscode = (typeof acquireVsCodeApi !== 'undefined') ? acquireVsCodeApi() : null;
window.addEventListener('load', () => { setTimeout(() => document.getElementById('loader').classList.add('hidden'), 400); });
const _errs = [];
const origErr = console.error;
console.error = function(...args) {
    _errs.push(args.join(' '));
    origErr.apply(console, args);
};
</script>
<script>${audioEngineJs}</script>
<script>${themesJs}</script>
<script>${jukeboxJs}</script>
<script>${dashboardJs}</script>
<script>${acestepJs}</script>
<script>
(function() {
    // --- AUTO DJ Integration ---
    const hwGPU = document.getElementById('hw-gpu');
    const hwVRAM = document.getElementById('hw-vram');
    const hwCPU = document.getElementById('hw-cpu');
    const hwRAM = document.getElementById('hw-ram');
    const hwTier = document.getElementById('hw-tier');
    const autoDjStatus = document.getElementById('auto-dj-status');
    const metaBpm = document.getElementById('meta-bpm');
    const metaKey = document.getElementById('meta-key');
    const metaTs = document.getElementById('meta-ts');
    const metaTitle = document.getElementById('meta-title');
    const overlayBpm = document.getElementById('overlay-bpm');
    const overlayKey = document.getElementById('overlay-key');
    const overlayTs = document.getElementById('overlay-ts');
    const overlayTitle = document.getElementById('overlay-title');
    const trackOverlay = document.getElementById('track-overlay');
    const trackMeta = document.getElementById('track-meta');

    function setText(el, txt) { if(el) el.textContent = txt; }
    function setHtml(el, html) { if(el) el.innerHTML = html; }

    // Hardware polling
    function fetchHardware() {
        if(vscode) vscode.postMessage({command:'fetchHardware'});
    }
    // Auto DJ status polling
    function fetchAutoDJStatus() {
        if(vscode) vscode.postMessage({command:'fetchAutoDJStatus'});
    }

    // Button handlers
    const btnLaunch = document.getElementById('btn-launch-webui');
    const btnKill = document.getElementById('btn-kill-autodj');
    const btnOptimize = document.getElementById('btn-optimize');

    if(btnLaunch) {
        btnLaunch.addEventListener('click', () => {
            if(vscode) vscode.postMessage({command:'launchWebUI'});
            setText(autoDjStatus, 'Launching Web UI...');
        });
    }
    if(btnKill) {
        btnKill.addEventListener('click', () => {
            if(vscode) vscode.postMessage({command:'killAutoDJ'});
            setText(autoDjStatus, 'Killing processes...');
        });
    }
    if(btnOptimize) {
        btnOptimize.addEventListener('click', () => {
            if(vscode) vscode.postMessage({command:'optimizeSystem'});
            setText(autoDjStatus, 'Optimizing system...');
        });
    }

    // Message handler from extension
    window.addEventListener('message', (event) => {
        const msg = event.data;
        if(!msg) return;
        switch(msg.command) {
            case 'hardwareUpdate':
                if(msg.data) {
                    setText(hwGPU, msg.data.gpu_name || '---');
                    setText(hwVRAM, msg.data.vram_gb ? msg.data.vram_gb + ' GB' : '---');
                    setText(hwCPU, msg.data.cpu_cores ? msg.data.cpu_cores + ' cores' : '---');
                    setText(hwRAM, msg.data.ram_gb ? msg.data.ram_gb + ' GB' : '---');
                    setText(hwTier, msg.data.tier || '---');
                }
                break;
            case 'autoDJStatusUpdate':
                if(msg.data && msg.data.ok) {
                    const d = msg.data;
                    setText(metaBpm, d.bpm || '---');
                    setText(metaKey, d.key || '---');
                    setText(metaTs, d.time_signature || '---');
                    setText(metaTitle, d.title || '');
                    setText(overlayBpm, d.bpm || '---');
                    setText(overlayKey, d.key || '---');
                    setText(overlayTs, d.time_signature || '---');
                    setText(overlayTitle, d.title || '');
                    if(d.bpm || d.title) {
                        trackOverlay.classList.add('visible');
                        trackMeta.style.opacity = '1';
                    }
                } else {
                    trackOverlay.classList.remove('visible');
                    trackMeta.style.opacity = '0';
                }
                break;
            case 'webuiLaunched':
                if(msg.data && msg.data.ok) {
                    setText(autoDjStatus, msg.data.already_running ? 'Web UI already running (PID ' + msg.data.pid + ')' : 'Web UI launched (PID ' + msg.data.pid + ')');
                } else {
                    setText(autoDjStatus, 'Launch failed: ' + (msg.data && msg.data.error ? msg.data.error : 'unknown'));
                }
                break;
            case 'autoDJKilled':
                if(msg.data && msg.data.ok) {
                    setText(autoDjStatus, 'Killed ' + (msg.data.killed ? msg.data.killed.length : 0) + ' process(es)');
                } else {
                    setText(autoDjStatus, 'Kill failed: ' + (msg.data && msg.data.error ? msg.data.error : 'unknown'));
                }
                break;
            case 'systemOptimized':
                if(msg.data && msg.data.ok) {
                    setText(autoDjStatus, 'Optimized: ' + (msg.data.freed ? msg.data.freed.join('; ') : 'done'));
                } else {
                    setText(autoDjStatus, 'Optimize failed: ' + (msg.data && msg.data.error ? msg.data.error : 'unknown'));
                }
                break;
        }
    });

    // Start polling
    fetchHardware();
    setInterval(fetchHardware, 15000);
    fetchAutoDJStatus();
    setInterval(fetchAutoDJStatus, 3000);

    try {
        if (typeof initInfiniteJukebox === 'function') {
            initInfiniteJukebox();
        }
    } catch (e) { console.error('Bootstrap error:', e); }
})();
</script>
<pre id="errors" style="position:fixed;bottom:0;left:0;right:0;z-index:999;background:rgba(0,0,0,0.8);color:#ff2a2a;padding:0.5rem;font-size:0.7rem;max-height:120px;overflow:auto;pointer-events:none;font-family:var(--jet-mono);"></pre>
</body>
</html>`;
    }

    private _minimalJukeboxJs(): string {
        return `class InfiniteJukeboxFluid{constructor(c,o={}){this.canvas=c;this.gl=c.getContext('webgl',{alpha:true,depth:false,stencil:false,antialias:false});this.simResolution=o.simResolution||256;this.dyeResolution=o.dyeResolution||1024;this.densityDissipation=o.densityDissipation??0.99;this.velocityDissipation=o.velocityDissipation??0.98;this.pressureIterations=o.pressureIterations||20;this.curlStrength=o.curlStrength||30;this.splatRadius=o.splatRadius||0.003;this.running=false;this.pointers=[{id:-1,x:0,y:0,dx:0,dy:0,down:false}];this.splats=[];this.resize();window.addEventListener('resize',()=>this.resize());}resize(){const dpr=window.devicePixelRatio||1;this.canvas.width=Math.round(this.canvas.clientWidth*dpr);this.canvas.height=Math.round(this.canvas.clientHeight*dpr);}start(){if(this.running)return;this.running=true;const loop=()=>{if(!this.running)return;this.step();this.render();requestAnimationFrame(loop);};requestAnimationFrame(loop);}stop(){this.running=false;}step(){if(this.splats.length>0)this.splats=[];}render(){const gl=this.gl;gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.clearColor(0.02,0.03,0.06,1);gl.clear(gl.COLOR_BUFFER_BIT);}}function initInfiniteJukebox(){const c=document.getElementById('fluid-canvas');if(!c)return;const fluid=new InfiniteJukeboxFluid(c,{simResolution:256,dyeResolution:1024,pressureIterations:20,curlStrength:30});const audio=new InfiniteJukeboxAudio({fftSize:512,bpm:110});if(audio.onAudioFrame)audio.onAudioFrame(frame=>fluid.feedAudioFrame(frame));fluid.start();(async()=>{try{await audio.start();}catch(e){console.warn('[Jukebox] AudioContext blocked:',e);}})();const status=document.getElementById('status');if(status){status.textContent='● Live';status.classList.add('live');}window.jukeboxFluid=fluid;window.jukeboxAudio=audio;}`;
    }

    private _minimalAudioJs(): string {
        return `class InfiniteJukeboxAudio{constructor(o={}){this.ctx=new(window.AudioContext||window.webkitAudioContext)();this.fftSize=o.fftSize||512;this.smoothing=o.smoothing||0.85;this.masterGain=this.ctx.createGain();this.masterGain.gain.value=o.masterVolume??0.45;this.compressor=this.ctx.createDynamicsCompressor();this.compressor.threshold.value=-24;this.compressor.knee.value=12;this.compressor.ratio.value=12;this.compressor.attack.value=0.003;this.compressor.release.value=0.25;this.compressor.connect(this.masterGain);this.masterGain.connect(this.ctx.destination);this.analyser=this.ctx.createAnalyser();this.analyser.fftSize=this.fftSize*2;this.analyser.smoothingTimeConstant=this.smoothing;this.masterGain.connect(this.analyser);this.isPlaying=false;this.oscillators=[];this.bpm=o.bpm||110;this.scale=o.scale||[0,2,4,7,9];this.rootNote=o.rootNote||55;this._callbacks=[];}onAudioFrame(cb){this._callbacks.push(cb);}async start(){if(this.ctx.state==='suspended')await this.ctx.resume();this.isPlaying=true;this._scheduleLoop();this._analyzeLoop();}stop(){this.isPlaying=false;this.oscillators.forEach(o=>{try{o.stop();o.disconnect();}catch(e){}});this.oscillators=[];}_scheduleLoop(){if(!this.isPlaying)return;const now=this.ctx.currentTime;const beatDur=60/this.bpm;for(let beat=0;beat<4;beat++){const t=now+beat*beatDur;if(beat%2===0)this._triggerKick(t,beatDur);if(beat%2===1)this._triggerSnare(t,beatDur);const bassNote=this._midiToFreq(this.rootNote+this.scale[beat%this.scale.length]);this._triggerBass(t,bassNote,beatDur*1.2);}setTimeout(()=>this._scheduleLoop(),(4*beatDur*1000)-100);}_analyzeLoop(){if(!this.isPlaying)return;const data=new Uint8Array(this.analyser.frequencyBinCount);this.analyser.getByteFrequencyData(data);const bins=new Float32Array(data.length);for(let i=0;i<data.length;i++)bins[i]=data[i]/255;const frame={frequencyBins:bins,peak_amplitude:Math.max(...bins),zero_crossing_rate:0,spectral_centroid:0};this._callbacks.forEach(cb=>cb(frame));requestAnimationFrame(()=>this._analyzeLoop());}_triggerKick(t,beatDur){const osc=this.ctx.createOscillator();const gain=this.ctx.createGain();osc.type='sine';osc.frequency.setValueAtTime(120,t);osc.frequency.exponentialRampToValueAtTime(55,t+0.25);gain.gain.setValueAtTime(0,t);gain.gain.linearRampToValueAtTime(0.9,t+0.02);gain.gain.exponentialRampToValueAtTime(0.01,t+0.35);osc.connect(gain);gain.connect(this.compressor);osc.start(t);osc.stop(t+0.4);this.oscillators.push(osc);}_triggerSnare(t,beatDur){const noise=this.ctx.createBufferSource();const buf=this.ctx.createBuffer(1,this.ctx.sampleRate*0.2,this.ctx.sampleRate);const d=buf.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;noise.buffer=buf;const f=this.ctx.createBiquadFilter();f.type='bandpass';f.frequency.value=3000;const g=this.ctx.createGain();g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(0.35,t+0.005);g.gain.exponentialRampToValueAtTime(0.01,t+0.18);noise.connect(f);f.connect(g);g.connect(this.compressor);noise.start(t);noise.stop(t+0.2);}_triggerBass(t,freq,dur){const osc=this.ctx.createOscillator();osc.type='triangle';osc.frequency.value=freq;const f=this.ctx.createBiquadFilter();f.type='lowpass';f.frequency.setValueAtTime(350,t);f.frequency.exponentialRampToValueAtTime(80,t+dur);const g=this.ctx.createGain();g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(0.55,t+0.04);g.gain.exponentialRampToValueAtTime(0.01,t+dur);osc.connect(f);f.connect(g);g.connect(this.compressor);osc.start(t);osc.stop(t+dur+0.1);this.oscillators.push(osc);}_midiToFreq(m){return 440*Math.pow(2,(m-69)/12);}}`;
    }

    private _minimalDashboardJs(): string {
        return `class MainBreakerDashboard{constructor(){this.panel=document.getElementById('dash-panel');this.toggleBtn=document.getElementById('dash-toggle');this.closeBtn=document.getElementById('dash-close');this.led=document.getElementById('breaker-led');this.breakerLabel=document.getElementById('breaker-label');this.breakerReason=document.getElementById('breaker-reason');this.resetBtn=document.getElementById('breaker-reset');this.sliders={viscosity:document.getElementById('slider-viscosity'),velocity:document.getElementById('slider-velocity'),frequency:document.getElementById('slider-frequency'),colortemp:document.getElementById('slider-colortemp'),bloom:document.getElementById('slider-bloom'),sunrays:document.getElementById('slider-sunrays'),dither:document.getElementById('slider-dither'),syllabic:document.getElementById('slider-syllabic'),negative:document.getElementById('slider-negative'),bpm:document.getElementById('slider-bpm')};this.readouts={viscosity:document.getElementById('val-viscosity'),velocity:document.getElementById('val-velocity'),frequency:document.getElementById('val-frequency'),colortemp:document.getElementById('val-colortemp'),bloom:document.getElementById('val-bloom'),sunrays:document.getElementById('val-sunrays'),dither:document.getElementById('val-dither'),syllabic:document.getElementById('val-syllabic'),negative:document.getElementById('val-negative'),bpm:document.getElementById('val-bpm')};this.moodSelect=document.getElementById('select-mood');this.fpsEl=document.getElementById('telemetry-fps');this.qualityEl=document.getElementById('telemetry-quality');this.gpuFills=[document.getElementById('gpu-0'),document.getElementById('gpu-1'),document.getElementById('gpu-2'),document.getElementById('gpu-3'),document.getElementById('gpu-4')];this.gpuPcts=[document.getElementById('gpu-0-pct'),document.getElementById('gpu-1-pct'),document.getElementById('gpu-2-pct'),document.getElementById('gpu-3-pct'),document.getElementById('gpu-4-pct')];this.sparkCanvas=document.getElementById('frame-sparkline');this.sparkCtx=this.sparkCanvas.getContext('2d');this.frameHistory=new Array(120).fill(16.67);this.debounceTimer=null;this.eventSource=null;this.statusInterval=null;this.lastFrameTime=performance.now();this._bindPanelToggle();this._bindSliders();this._bindMoodSelect();this._bindResetButton();this._startStatusPolling();this._startEventStream();this._startFrameLoop();}_bindPanelToggle(){this.toggleBtn.addEventListener('click',()=>{this.panel.classList.add('open');this.toggleBtn.classList.add('active');});this.closeBtn.addEventListener('click',()=>{this.panel.classList.remove('open');this.toggleBtn.classList.remove('active');});document.addEventListener('click',(e)=>{const inside=this.panel.contains(e.target)||this.toggleBtn.contains(e.target);if(!inside&&this.panel.classList.contains('open')){this.panel.classList.remove('open');this.toggleBtn.classList.remove('active');}});}_bindSliders(){const scales={viscosity:{min:0,max:1,div:100,fixed:2},velocity:{min:0.5,max:2,div:100,fixed:2},frequency:{min:0,max:1,div:100,fixed:2},colortemp:{min:2000,max:10000,div:1,fixed:0,suffix:' K'},bloom:{min:0,max:1,div:100,fixed:2},sunrays:{min:0,max:2,div:100,fixed:2},dither:{min:0,max:0.1,div:1000,fixed:3},syllabic:{min:0.1,max:1,div:100,fixed:2},negative:{min:0,max:0.5,div:100,fixed:2},bpm:{min:60,max:180,div:1,fixed:0}};for(const[key,slider]of Object.entries(this.sliders)){if(!slider)continue;slider.addEventListener('input',()=>{const s=scales[key];const raw=parseFloat(slider.value);const scaled=s.min+(raw/s.div)*(s.max-s.min);const display=scaled.toFixed(s.fixed)+(s.suffix||'');this.readouts[key].textContent=display;this._applyLiveConfig(key,scaled);});slider.addEventListener('change',()=>{this._debouncedConfigUpdate();});}}_applyLiveConfig(key,value){const fluid=window.jukeboxFluid;const audio=window.jukeboxAudio;if(!fluid&&!audio)return;switch(key){case'viscosity':if(fluid)fluid.applyConfig({viscosity:value});break;case'velocity':if(fluid)fluid.applyConfig({flowVelocity:value});break;case'frequency':if(fluid)fluid.applyConfig({splatRadius:0.001+value*0.008});break;case'colortemp':if(fluid)fluid.applyConfig({colorTemp:value});break;case'bloom':if(fluid)fluid.applyConfig({bloomIntensity:value});break;case'sunrays':if(fluid)fluid.applyConfig({sunraysWeight:value});break;case'dither':if(fluid)fluid.applyConfig({ditherStrength:value});break;case'syllabic':if(audio)audio.applyConfig({maxSyllabicDensity:value});break;case'negative':if(audio)audio.applyConfig({minNegativeSpaceRatio:value});break;case'bpm':if(audio)audio.applyConfig({bpm:value});break;}}_bindMoodSelect(){this.moodSelect.addEventListener('change',()=>{const mood=this.moodSelect.value;const fluid=window.jukeboxFluid;const audio=window.jukeboxAudio;const moodMap={ambient:{temp:6500,bloom:0.3,sunrays:1,dither:0.03},energetic:{temp:4500,bloom:0.6,sunrays:1.5,dither:0.02},dark:{temp:2800,bloom:0.15,sunrays:0.3,dither:0.05},chaos:{temp:7500,bloom:0.8,sunrays:2,dither:0.01},minimal:{temp:9000,bloom:0.1,sunrays:0,dither:0.08}};const preset=moodMap[mood]||moodMap.ambient;if(fluid){fluid.applyConfig({colorTemp:preset.temp,bloomIntensity:preset.bloom,sunraysWeight:preset.sunrays,ditherStrength:preset.dither});}if(audio){audio.applyConfig({mood});}this._syncSlider('colortemp',preset.temp,2000,10000);this._syncSlider('bloom',preset.bloom,0,1);this._syncSlider('sunrays',preset.sunrays,0,2);this._syncSlider('dither',preset.dither,0,0.1);this._debouncedConfigUpdate();});}_syncSlider(key,value,min,max){const slider=this.sliders[key];const readout=this.readouts[key];if(!slider)return;const scales={colortemp:{div:1,fixed:0,suffix:' K'},bloom:{div:100,fixed:2},sunrays:{div:100,fixed:2},dither:{div:1000,fixed:3}};const s=scales[key];const pct=(value-min)/(max-min);slider.value=Math.round(pct*s.div);readout.textContent=value.toFixed(s.fixed)+(s.suffix||'');}_bindResetButton(){this.resetBtn.addEventListener('click',async()=>{this.resetBtn.disabled=true;try{const resp=await fetch('/jukebox/api/breaker/reset',{method:'POST',headers:{'Content-Type':'application/json'}});if(!resp.ok)throw new Error('Breaker reset failed');const audio=window.jukeboxAudio;if(audio)audio.applyConfig({lockState:'free'});}catch(err){console.error('[Dashboard] Breaker reset error:',err);}finally{setTimeout(()=>{this.resetBtn.disabled=false;},1500);}});}_debouncedConfigUpdate(){if(this.debounceTimer)clearTimeout(this.debounceTimer);this.debounceTimer=setTimeout(()=>{this._sendConfig();},200);}async _sendConfig(){const payload={viscosity:parseFloat(this.sliders.viscosity.value)/100,flowVelocity:0.5+(parseFloat(this.sliders.velocity.value)/100)*1.5,frequencyResponse:parseFloat(this.sliders.frequency.value)/100,colorTemp:parseInt(this.sliders.colortemp.value,10),bloomIntensity:parseFloat(this.sliders.bloom.value)/100,sunraysWeight:parseFloat(this.sliders.sunrays.value)/100*2,ditherStrength:parseFloat(this.sliders.dither.value)/1000,maxSyllabicDensity:0.1+(parseFloat(this.sliders.syllabic.value)/100)*0.9,minNegativeSpaceRatio:parseFloat(this.sliders.negative.value)/100*0.5,bpm:parseInt(this.sliders.bpm.value,10),mood:this.moodSelect.value};try{const resp=await fetch('/jukebox/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!resp.ok)throw new Error('Config POST failed');}catch(err){console.error('[Dashboard] Config update error:',err);}}_startStatusPolling(){this.statusInterval=setInterval(async()=>{try{const resp=await fetch('/jukebox/api/status');if(!resp.ok)return;const data=await resp.json();this._updateBreakerStatus(data);}catch(err){}},500);}_startEventStream(){try{this.eventSource=new EventSource('/jukebox/api/stream');this.eventSource.addEventListener('open',()=>{console.log('[Dashboard] SSE bus connected.');});this.eventSource.addEventListener('message',(e)=>{try{const data=JSON.parse(e.data);this._handleStreamData(data);}catch(parseErr){console.error('[Dashboard] SSE parse error:',parseErr);}});this.eventSource.addEventListener('error',()=>{this.eventSource.close();this.eventSource=null;setTimeout(()=>this._startEventStream(),5000);});}catch(err){console.error('[Dashboard] SSE init error:',err);}}_updateBreakerStatus(data){const status=(data.breaker_lock_state||'free').toLowerCase();this.led.classList.remove('green','yellow','red');if(status==='free'||status==='normal'){this.led.classList.add('green');this.breakerLabel.textContent='NORM';this.breakerLabel.style.color='var(--success)';}else if(status==='locked'){this.led.classList.add('yellow');this.breakerLabel.textContent='WARN';this.breakerLabel.style.color='var(--warning)';}else{this.led.classList.add('red');this.breakerLabel.textContent='OVERRIDE';this.breakerLabel.style.color='var(--danger)';}const reason=data.breaker_reason||'';this.breakerReason.textContent=reason;}_handleStreamData(data){if(Array.isArray(data.gpu_utilization)){data.gpu_utilization.forEach((pct,idx)=>{if(idx>=this.gpuFills.length)return;const clamped=Math.max(0,Math.min(100,pct));this.gpuFills[idx].style.width=clamped+'%';this.gpuPcts[idx].textContent=Math.round(clamped)+'%';});}if(typeof data.frame_time_ms==='number'){this.frameHistory.push(data.frame_time_ms);this.frameHistory.shift();}if(typeof data.fps==='number'){this.fpsEl.textContent=Math.round(data.fps);}if(data.quality_level){this.qualityEl.innerHTML='<span class="quality-badge">'+data.quality_level.toUpperCase()+'</span>';}}_startFrameLoop(){const tick=()=>{this._measureFrameTime();this._drawSparkline();requestAnimationFrame(tick);};requestAnimationFrame(tick);}_measureFrameTime(){const now=performance.now();const delta=now-this.lastFrameTime;this.lastFrameTime=now;if(delta>0&&delta<200){this.frameHistory.push(delta);this.frameHistory.shift();}}_drawSparkline(){const ctx=this.sparkCtx;const w=this.sparkCanvas.width;const h=this.sparkCanvas.height;ctx.clearRect(0,0,w,h);if(this.frameHistory.length<2)return;const maxVal=Math.max(...this.frameHistory,33.33);const range=maxVal||1;ctx.strokeStyle='rgba(0,229,255,0.85)';ctx.lineWidth=1.5;ctx.beginPath();for(let i=0;i<this.frameHistory.length;i++){const x=(i/(this.frameHistory.length-1))*w;const y=(1-(this.frameHistory[i]/range))*(h-4)+2;if(i===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);}ctx.stroke();const refY=(1-(16.67/range))*(h-4)+2;if(refY>0&&refY<h){ctx.strokeStyle='rgba(0,229,255,0.15)';ctx.lineWidth=1;ctx.setLineDash([3,3]);ctx.beginPath();ctx.moveTo(0,refY);ctx.lineTo(w,refY);ctx.stroke();ctx.setLineDash([]);}}destroy(){if(this.statusInterval)clearInterval(this.statusInterval);if(this.eventSource)this.eventSource.close();if(this.debounceTimer)clearTimeout(this.debounceTimer);}}if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',()=>{window.mainBreakerDashboard=new MainBreakerDashboard();});}else{window.mainBreakerDashboard=new MainBreakerDashboard();}`;
    }
}
