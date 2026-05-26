import * as vscode from 'vscode';
import { httpGet, httpPost } from '../services/httpUtil';

export class OrbitScribeSidebarProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'orbitscribe.splashView';
    private _view?: vscode.WebviewView;

    constructor(private readonly _extensionUri: vscode.Uri) {}

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri],
        };

        try {
            webviewView.webview.html = this._getHtml(webviewView.webview);
        } catch (err: any) {
            console.error('[OrbitScribe] Failed to generate sidebar HTML:', err);
            webviewView.webview.html = getFallbackHtml();
        }

        webviewView.webview.onDidReceiveMessage(async (message) => {
            try {
                switch (message.command) {
                    case 'openPanel': {
                        const { SwarmPanel } = await import('./SwarmPanel');
                        SwarmPanel.createOrShow(this._extensionUri, message.mode);
                        setTimeout(() => {
                            SwarmPanel.currentPanel?.sendMessage({ command: 'setAutonomy', autonomy: message.autonomy || 'default' });
                            if (message.temperature !== undefined) {
                                SwarmPanel.currentPanel?.sendMessage({ command: 'setTemperature', temperature: message.temperature });
                            }
                            if (message.orchestrator !== undefined) {
                                SwarmPanel.currentPanel?.sendMessage({ command: 'setOrchestrator', orchestrator: message.orchestrator });
                            }
                            if (message.subagent_mode !== undefined) {
                                SwarmPanel.currentPanel?.sendMessage({ command: 'setSubagentMode', subagent_mode: message.subagent_mode });
                            }
                        }, 400);
                        break;
                    }
                    case 'openSwarmDeck': {
                        const { SwarmPanel } = await import('./SwarmPanel');
                        const { CommandDeckPanel } = await import('./CommandDeckPanel');
                        SwarmPanel.createOrShow(this._extensionUri, message.mode || 'swarm');
                        setTimeout(() => {
                            SwarmPanel.currentPanel?.sendMessage({ command: 'setAutonomy', autonomy: message.autonomy || 'default' });
                            if (message.temperature !== undefined) {
                                SwarmPanel.currentPanel?.sendMessage({ command: 'setTemperature', temperature: message.temperature });
                            }
                            if (message.orchestrator !== undefined) {
                                SwarmPanel.currentPanel?.sendMessage({ command: 'setOrchestrator', orchestrator: message.orchestrator });
                            }
                            if (message.subagent_mode !== undefined) {
                                SwarmPanel.currentPanel?.sendMessage({ command: 'setSubagentMode', subagent_mode: message.subagent_mode });
                            }
                        }, 400);
                        setTimeout(() => {
                            CommandDeckPanel.createOrShow(this._extensionUri);
                        }, 500);
                        break;
                    }
                    case 'sendMessage': {
                        const { SwarmPanel } = await import('./SwarmPanel');
                        SwarmPanel.createOrShow(this._extensionUri, message.mode);
                        setTimeout(() => {
                            if (message.temperature !== undefined) {
                                SwarmPanel.currentPanel?.sendMessage({ command: 'setTemperature', temperature: message.temperature });
                            }
                            SwarmPanel.currentPanel?.sendMessage({
                                command: 'sendText',
                                text: message.text,
                                mode: message.mode
                            });
                        }, 300);
                        break;
                    }
                    case 'copyText': {
                        const text = message.text;
                        if (text) {
                            await vscode.env.clipboard.writeText(text);
                            webviewView.webview.postMessage({ command: 'toast', message: 'Copied to clipboard' });
                        }
                        break;
                    }
                    case 'typeText': {
                        const editor = vscode.window.activeTextEditor;
                        if (editor) {
                            editor.edit((editBuilder) => {
                                editBuilder.insert(editor.selection.active, message.text);
                            });
                            webviewView.webview.postMessage({ command: 'toast', message: 'Typed into editor' });
                        } else {
                            webviewView.webview.postMessage({ command: 'toast', message: 'No active editor' });
                        }
                        break;
                    }
                    case 'voiceInput': {
                        const { SwarmPanel } = await import('./SwarmPanel');
                        SwarmPanel.createOrShow(this._extensionUri, 'ask');
                        setTimeout(() => {
                            SwarmPanel.currentPanel?.sendMessage({ command: 'triggerVoice' });
                        }, 300);
                        break;
                    }
                    case 'newChat': {
                        const { SwarmPanel } = await import('./SwarmPanel');
                        SwarmPanel.createOrShow(this._extensionUri, message.mode || 'ask');
                        setTimeout(() => {
                            SwarmPanel.currentPanel?.sendMessage({ command: 'resetChat' });
                        }, 300);
                        break;
                    }
                    case 'checkVoiceBackend': {
                        try {
                            const resp = await httpGet('http://127.0.0.1:58080/api/status');
                            webviewView.webview.postMessage({ command: 'voiceBackendStatus', ok: resp.ok });
                        } catch {
                            webviewView.webview.postMessage({ command: 'voiceBackendStatus', ok: false });
                        }
                        break;
                    }
                    case 'startVoiceBackend': {
                        try {
                            await vscode.commands.executeCommand('orbitscribe.restartVoiceBackend');
                            await new Promise(r => setTimeout(r, 2000));
                            const resp = await httpGet('http://127.0.0.1:58080/api/status');
                            webviewView.webview.postMessage({ command: 'voiceBackendStarted', ok: resp.ok });
                        } catch (e: any) {
                            webviewView.webview.postMessage({ command: 'voiceBackendStarted', ok: false, error: e.message || 'Failed to start' });
                        }
                        break;
                    }
                    case 'startVoiceRecord': {
                        try {
                            const resp = await httpPost('http://127.0.0.1:58080/api/record');
                            const data: any = await resp.json();
                            webviewView.webview.postMessage({ command: 'voiceRecordStarted', ok: data.ok, error: data.error });
                        } catch (e: any) {
                            webviewView.webview.postMessage({ command: 'voiceRecordStarted', ok: false, error: 'Voice engine not reachable' });
                        }
                        break;
                    }
                    case 'getVoiceStatus': {
                        try {
                            const resp = await httpGet('http://127.0.0.1:58080/api/status');
                            const data: any = await resp.json();
                            webviewView.webview.postMessage({ command: 'voiceStatusUpdate', status: data.status, message: data.message });
                        } catch {
                            webviewView.webview.postMessage({ command: 'voiceStatusUpdate', status: 'offline', message: '' });
                        }
                        break;
                    }
                    case 'webviewReady': {
                        console.log('[OrbitScribe] Sidebar webview reported ready');
                        break;
                    }
                    case 'createPlanOptions': {
                        try {
                            const resp = await httpPost('http://127.0.0.1:58081/api/plan/options', { goal: message.goal });
                            const data = await resp.json();
                            webviewView.webview.postMessage({ command: 'planOptionsCreated', success: data.plan_id !== undefined, plan: data, error: data.error });
                        } catch (e: any) {
                            webviewView.webview.postMessage({ command: 'planOptionsCreated', success: false, error: e.message || 'Backend unreachable' });
                        }
                        break;
                    }
                    case 'selectPlanOption': {
                        try {
                            const resp = await httpPost('http://127.0.0.1:58081/api/plan/options/select', { plan_id: message.plan_id, option_id: message.option_id });
                            const data = await resp.json();
                            webviewView.webview.postMessage({ command: 'planOptionSelected', success: data.status === 'selected', plan: data });
                            // Open the swarm panel in plan mode with the goal
                            const { SwarmPanel } = await import('./SwarmPanel');
                            SwarmPanel.createOrShow(this._extensionUri, 'plan');
                            setTimeout(() => {
                                SwarmPanel.currentPanel?.sendMessage({ command: 'sendText', text: message.goal, mode: 'plan' });
                            }, 400);
                        } catch (e: any) {
                            webviewView.webview.postMessage({ command: 'planOptionSelected', success: false, error: e.message || 'Backend unreachable' });
                        }
                        break;
                    }
                    case 'getNodes': {
                        try {
                            const resp = await httpGet('http://127.0.0.1:58081/api/nodes');
                            const data = await resp.json();
                            webviewView.webview.postMessage({ command: 'nodesList', nodes: data.nodes || [] });
                        } catch (e: any) {
                            webviewView.webview.postMessage({ command: 'nodesList', nodes: [] });
                        }
                        break;
                    }
                    case 'discoverNodes': {
                        try {
                            const resp = await httpGet('http://127.0.0.1:58081/api/nodes/discover?timeout=3');
                            const data = await resp.json();
                            webviewView.webview.postMessage({ command: 'nodesDiscovered', success: data.success, discovered: data.discovered, nodes: data.nodes || [], error: data.error });
                        } catch (e: any) {
                            webviewView.webview.postMessage({ command: 'nodesDiscovered', success: false, error: e.message || 'Backend unreachable' });
                        }
                        break;
                    }
                    case 'forwardTask': {
                        try {
                            const resp = await httpPost('http://127.0.0.1:58081/api/nodes/forward', { goal: message.goal, prefer_large_model: false });
                            const data = await resp.json();
                            webviewView.webview.postMessage({ command: 'taskForwarded', success: data.success, node_id: data.node_id, error: data.error });
                        } catch (e: any) {
                            webviewView.webview.postMessage({ command: 'taskForwarded', success: false, error: e.message || 'Backend unreachable' });
                        }
                        break;
                    }
                    case 'checkNodeHealth': {
                        try {
                            const resp = await httpGet('http://127.0.0.1:58081/api/nodes/health');
                            const data = await resp.json();
                            const node = (data.nodes || []).find((n: any) => n.node_id === message.node_id);
                            webviewView.webview.postMessage({ command: 'nodeHealth', node_id: message.node_id, healthy: !!node });
                        } catch (e: any) {
                            webviewView.webview.postMessage({ command: 'nodeHealth', node_id: message.node_id, healthy: false });
                        }
                        break;
                    }
                }
            } catch (handlerErr: any) {
                console.error('[OrbitScribe] Message handler error:', handlerErr);
            }
        });
    }

    public sendMessage(message: any) {
        if (this._view) {
            this._view.webview.postMessage(message);
        }
    }

    private _getHtml(webview: vscode.Webview): string {
        const nonce = getNonce();

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}'; connect-src http://127.0.0.1:*;">
    <title>OrbitScribe</title>
    <style>
        :root {
            --bg: #0f1117;
            --panel: rgba(26, 29, 38, 0.6);
            --panel-solid: #1a1d26;
            --text: #e2e8f0;
            --muted: #94a3b8;
            --accent: #8b5cf6;
            --accent-hover: #7c3aed;
            --accent-light: #a78bfa;
            --accent-dark: #7c3aed;
            --border: rgba(45, 49, 66, 0.5);
            --border-solid: #2d3142;
            --recording: #f97316;
            --recording-glow: rgba(249, 115, 22, 0.4);
            --success: #22c55e;
            --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: var(--font);
            padding: 16px 12px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }
        .mic-btn {
            background: transparent;
            border: none;
            padding: 0;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-bottom: 12px;
            transition: transform 0.2s ease;
            position: relative;
        }
        .mic-btn:hover { transform: scale(1.08); }
        .mic-btn:active { transform: scale(0.95); }
        .mic-btn.listening { animation: micPulse 1.2s infinite; }
        .mic-btn.listening .logo { filter: drop-shadow(0 0 20px var(--recording-glow)); }
        @keyframes micPulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
        .logo {
            width: 96px;
            height: 96px;
            filter: drop-shadow(0 0 16px rgba(139, 92, 246, 0.35));
        }
        .mic-status {
            font-size: 11px;
            color: var(--muted);
            margin-top: 4px;
            min-height: 16px;
            text-align: center;
        }
        .mic-status.listening { color: var(--recording); font-weight: 600; }
        .mode-tabs {
            display: flex;
            gap: 6px;
            margin-bottom: 16px;
            width: 100%;
            justify-content: center;
        }
        .mode-tab {
            padding: 6px 12px;
            border-radius: 8px;
            border: 1px solid var(--border-solid);
            background: transparent;
            color: var(--muted);
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s;
            flex: 1;
            text-align: center;
        }
        .mode-tab:hover { color: var(--text); border-color: var(--accent); }
        .mode-tab.active { background: var(--accent); border-color: var(--accent); color: #fff; }
        .result-panel {
            width: 100%;
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 12px;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
        }
        .result-panel h2 {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
            margin-bottom: 10px;
            font-weight: 600;
        }
        .latest-result {
            font-size: 15px;
            line-height: 1.5;
            min-height: 48px;
            word-break: break-word;
            margin-bottom: 12px;
        }
        .latest-result.empty { color: var(--muted); font-style: italic; }
        .actions { display: flex; gap: 8px; flex-wrap: wrap; }
        .btn {
            padding: 6px 14px;
            border-radius: 10px;
            border: 1px solid var(--border-solid);
            background: rgba(15, 17, 23, 0.5);
            color: var(--text);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
        }
        .btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
        .btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .btn svg { width: 14px; height: 14px; }
        .input-area { width: 100%; margin-bottom: 12px; }
        .input-label {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--muted);
            margin-bottom: 6px;
            font-weight: 600;
        }
        .chat-input-wrap { display: flex; gap: 8px; align-items: flex-end; }
        .chat-input {
            flex: 1;
            background: rgba(15, 17, 23, 0.5);
            border: 1px solid var(--border-solid);
            border-radius: 12px;
            padding: 10px 12px;
            color: var(--text);
            font-size: 13px;
            font-family: inherit;
            resize: vertical;
            min-height: 64px;
            max-height: 140px;
            outline: none;
            width: 100%;
        }
        .chat-input:focus { border-color: var(--accent); }
        .send-btn {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            border: none;
            background: var(--accent);
            color: #fff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: background 0.15s;
        }
        .send-btn:hover { background: var(--accent-hover); }
        .send-btn svg { width: 16px; height: 16px; }
        .feature-btn {
            width: 100%;
            padding: 12px;
            border-radius: 12px;
            border: 1px solid var(--border-solid);
            background: rgba(15, 17, 23, 0.4);
            color: var(--text);
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-bottom: 10px;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
        }
        .feature-btn:hover { border-color: var(--accent); background: var(--panel); }
        .feature-btn svg { width: 16px; height: 16px; }
        footer { margin-top: auto; padding-top: 20px; text-align: center; color: var(--muted); font-size: 12px; }
        .toast {
            position: fixed;
            bottom: 16px;
            left: 50%;
            transform: translateX(-50%) translateY(80px);
            background: var(--panel-solid);
            border: 1px solid var(--border-solid);
            color: var(--text);
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 500;
            opacity: 0;
            transition: all 0.3s ease;
            pointer-events: none;
            z-index: 100;
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
        }
        .toast.show { transform: translateX(-50%) translateY(0); opacity: 1; }
        .settings-panel { display: none; width: 100%; background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 12px; margin-bottom: 12px; }
        .settings-panel.active { display: block; }
        .settings-panel h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 10px; font-weight: 600; }
        .setting-row { display: flex; align-items: center; justify-content: space-between; padding: 6px 0; font-size: 13px; }
        .setting-row label { color: var(--muted); font-size: 11px; text-transform: uppercase; }
        .setting-row select {
            background: var(--panel-solid);
            border: 1px solid var(--border-solid);
            border-radius: 6px;
            color: var(--text);
            padding: 4px 8px;
            font-size: 12px;
            outline: none;
        }
        .temp-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 13px; }
        .temp-row label { color: var(--muted); font-size: 12px; }
        .temp-slider { flex: 1; cursor: pointer; }
        .temp-value { min-width: 32px; text-align: right; font-variant-numeric: tabular-nums; font-size: 12px; }
        .theme-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-top: 6px; }
        .theme-btn { width: 100%; aspect-ratio: 1; border-radius: 8px; border: 2px solid transparent; cursor: pointer; transition: all 0.2s; }
        .theme-btn:hover { transform: scale(1.1); }
        .theme-btn.active { border-color: var(--text); box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px var(--accent); }
        .status-bar {
            display: flex;
            gap: 6px;
            width: 100%;
            margin-bottom: 12px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 4px 10px;
            border-radius: 20px;
            border: 1px solid var(--border-solid);
            background: rgba(15, 17, 23, 0.5);
            font-size: 11px;
            font-weight: 500;
            color: var(--muted);
            transition: all 0.3s ease;
            cursor: default;
        }
        .status-pill.online {
            border-color: rgba(34, 197, 94, 0.4);
            background: rgba(34, 197, 94, 0.08);
            color: #4ade80;
        }
        .status-pill.offline {
            border-color: rgba(239, 68, 68, 0.4);
            background: rgba(239, 68, 68, 0.08);
            color: #f87171;
        }
        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--muted);
            transition: all 0.3s ease;
        }
        .status-pill.online .status-dot {
            background: #22c55e;
            box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
        }
        .status-pill.offline .status-dot {
            background: #ef4444;
            box-shadow: 0 0 6px rgba(239, 68, 68, 0.5);
        }
        .history-panel { display: none; width: 100%; background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 12px; margin-bottom: 12px; max-height: 240px; overflow-y: auto; }
        .history-panel.active { display: block; }
        .plan-options-panel { display: none; width: 100%; background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 12px; margin-bottom: 12px; max-height: 400px; overflow-y: auto; }
        .plan-options-panel.active { display: block; }
        .plan-options-panel h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 10px; font-weight: 600; }
        .empty-plan { color: var(--muted); font-style: italic; font-size: 13px; padding: 8px 0; }
        .plan-option { padding: 10px; border: 1px solid var(--border); border-radius: 10px; margin-bottom: 8px; background: rgba(15,17,23,0.4); cursor: pointer; transition: all 0.15s; }
        .plan-option:hover { border-color: var(--accent); background: rgba(139,92,246,0.08); }
        .plan-option.selected { border-color: var(--accent); background: rgba(139,92,246,0.12); }
        .plan-option-title { font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
        .plan-option-desc { font-size: 12px; color: var(--muted); line-height: 1.4; margin-bottom: 6px; }
        .plan-option-meta { display: flex; gap: 8px; font-size: 11px; color: var(--muted); flex-wrap: wrap; }
        .plan-option-meta span { background: rgba(45,49,66,0.5); padding: 2px 6px; border-radius: 4px; }
        .remote-nodes-panel { display: none; width: 100%; background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 12px; margin-bottom: 12px; max-height: 300px; overflow-y: auto; }
        .remote-nodes-panel.active { display: block; }
        .remote-nodes-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .remote-nodes-header h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); font-weight: 600; }
        .remote-nodes-refresh { background: var(--accent); color: #fff; border: none; border-radius: 6px; padding: 4px 10px; font-size: 11px; cursor: pointer; }
        .remote-nodes-refresh:hover { background: var(--accent-hover); }
        .empty-nodes { color: var(--muted); font-style: italic; font-size: 13px; padding: 8px 0; }
        .node-item { padding: 8px; border: 1px solid var(--border); border-radius: 8px; margin-bottom: 6px; background: rgba(15,17,23,0.4); }
        .node-item.online { border-color: rgba(34,197,94,0.4); }
        .node-item.offline { border-color: rgba(239,68,68,0.4); opacity: 0.7; }
        .node-name { font-size: 12px; font-weight: 600; color: var(--text); }
        .node-meta { font-size: 11px; color: var(--muted); margin-top: 2px; }
        .node-actions { display: flex; gap: 6px; margin-top: 6px; }
        .node-btn { padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border); background: transparent; color: var(--text); font-size: 11px; cursor: pointer; }
        .node-btn:hover { border-color: var(--accent); color: var(--accent); }
        .node-btn.forward { background: var(--accent); color: #fff; border-color: var(--accent); }
        .node-btn.forward:hover { background: var(--accent-hover); }
        .history-item { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; line-height: 1.4; word-break: break-word; display: flex; align-items: center; justify-content: space-between; gap: 8px; }
        .history-item:last-child { border-bottom: none; }
        .history-item:hover { color: var(--accent-light); }
        .history-item-text { flex: 1; cursor: pointer; min-width: 0; }
        .history-item-meta { font-size: 11px; color: var(--muted); white-space: nowrap; }
        .history-delete { background: transparent; border: none; color: var(--muted); cursor: pointer; padding: 2px 6px; border-radius: 6px; font-size: 16px; line-height: 1; }
        .history-delete:hover { color: #ef4444; background: rgba(239,68,68,0.1); }
        .empty-history { color: var(--muted); font-style: italic; font-size: 13px; padding: 8px 0; }
        .new-chat-btn { width: 100%; padding: 12px; border-radius: 12px; border: 1px solid var(--accent); background: rgba(139,92,246,0.08); color: var(--accent-light); font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.15s; display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 10px; }
        .new-chat-btn:hover { background: rgba(139,92,246,0.15); }
    </style>
</head>
<body>
    <div class="status-bar" id="statusBar">
        <div class="status-pill" id="enginePill" title="OrbitScribe Backend">
            <span class="status-dot" id="engineDot"></span>
            <span class="status-label" id="engineLabel">Engine</span>
        </div>
        <div class="status-pill" id="ollamaPill" title="Ollama Local LLM">
            <span class="status-dot" id="ollamaDot"></span>
            <span class="status-label" id="ollamaLabel">Ollama</span>
        </div>
        <div class="status-pill" id="modelPill" title="Active Model">
            <span class="status-dot" id="modelDot"></span>
            <span class="status-label" id="modelLabel">Model</span>
        </div>
    </div>

    <button class="mic-btn" id="micBtn" title="Click to record">
        <svg class="logo" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="glow" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.3"/>
              <stop offset="100%" stop-color="#a78bfa" stop-opacity="0.1"/>
            </linearGradient>
          </defs>
          <circle cx="256" cy="256" r="244" fill="#0f111c" stroke="#8b5cf6" stroke-width="3" opacity="0.9"/>
          <circle cx="256" cy="256" r="244" fill="url(#glow)" opacity="0.3"/>
          <g fill="none" stroke="#7c3aed" stroke-width="2.5" opacity="0.8">
            <ellipse cx="256" cy="256" rx="220" ry="180" transform="rotate(25 256 256)"/>
            <ellipse cx="256" cy="256" rx="200" ry="190" transform="rotate(-15 256 256)"/>
            <ellipse cx="256" cy="256" rx="210" ry="170" transform="rotate(45 256 256)"/>
          </g>
          <circle cx="356" cy="166" r="4" fill="#a78bfa"/>
          <circle cx="446" cy="256" r="4" fill="#a78bfa"/>
          <circle cx="356" cy="346" r="4" fill="#a78bfa"/>
          <rect x="228" y="168" width="56" height="90" rx="28" fill="white"/>
          <g stroke="#c8d2e6" stroke-width="1.5" opacity="0.5">
            <line x1="240" y1="192" x2="272" y2="192"/>
            <line x1="240" y1="204" x2="272" y2="204"/>
            <line x1="240" y1="216" x2="272" y2="216"/>
            <line x1="240" y1="228" x2="272" y2="228"/>
          </g>
          <path d="M 212 250 A 44 26 0 0 0 300 250" fill="none" stroke="white" stroke-width="5" stroke-linecap="round"/>
          <line x1="256" y1="276" x2="256" y2="294" stroke="white" stroke-width="5" stroke-linecap="round"/>
          <line x1="238" y1="294" x2="274" y2="294" stroke="white" stroke-width="5" stroke-linecap="round"/>
        </svg>
        <div class="mic-status" id="micStatus">Tap to record</div>
    </button>

    <div class="mode-tabs">
        <button class="mode-tab active" data-mode="ask">Ask</button>
        <button class="mode-tab" data-mode="plan">Plan</button>
        <button class="mode-tab" data-mode="agent">Agent</button>
        <button class="mode-tab" data-mode="swarm">Swarm</button>
    </div>

    <div class="result-panel">
        <h2>Latest Result</h2>
        <div class="latest-result empty" id="latestResult">Your transcribed text will appear here...</div>
        <div class="actions">
            <button class="btn" id="copyBtn" title="Copy to clipboard">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                Copy
            </button>
            <button class="btn" id="typeBtn" title="Type into editor">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"></rect><path d="M6 8h.01M6 12h.01M6 16h.01M10 8h4M10 12h4M10 16h4M14 8h.01M14 12h.01M14 16h.01"></path></svg>
                Type
            </button>
            <button class="btn" id="clearBtn" title="Clear result">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                Clear
            </button>
        </div>
    </div>

    <div class="input-area">
        <div class="input-label">Type a message</div>
        <div class="chat-input-wrap">
            <textarea class="chat-input" id="chatInput" rows="2" placeholder="Ask, plan, or delegate..."></textarea>
            <button class="send-btn" id="sendBtn" title="Send">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
        </div>
    </div>

    <button class="new-chat-btn" id="newChatBtn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
        New Chat
    </button>

    <div class="history-panel" id="historyPanel">
        <div class="empty-history" id="historyEmpty">No saved sessions</div>
        <div id="historyList"></div>
    </div>

    <button class="feature-btn" id="ttsBtn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>
        Text to Speech
    </button>

    <button class="feature-btn" id="historyBtn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
        History
    </button>

    <button class="feature-btn" id="planOptionsBtn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>
        Plan Options
    </button>

    <div class="plan-options-panel" id="planOptionsPanel">
        <h2>Choose an Approach</h2>
        <div class="empty-plan" id="planOptionsEmpty">Enter a goal above and click Plan Options to generate approaches.</div>
        <div id="planOptionsList"></div>
    </div>

    <div class="settings-panel" id="settingsPanel">
        <h2>Settings</h2>
        <div class="setting-row">
            <span>Theme</span>
        </div>
        <div class="theme-grid" id="themeGrid">
            <button class="theme-btn active" data-theme="orbit" style="background:linear-gradient(135deg,#8b5cf6,#a78bfa);" title="Orbit (Purple)"></button>
            <button class="theme-btn" data-theme="neon" style="background:linear-gradient(135deg,#06b6d4,#22d3ee);" title="Neon (Cyan)"></button>
            <button class="theme-btn" data-theme="ember" style="background:linear-gradient(135deg,#ef4444,#f87171);" title="Ember (Red)"></button>
            <button class="theme-btn" data-theme="forest" style="background:linear-gradient(135deg,#22c55e,#4ade80);" title="Forest (Green)"></button>
            <button class="theme-btn" data-theme="sunset" style="background:linear-gradient(135deg,#f59e0b,#fb923c);" title="Sunset (Gold)"></button>
            <button class="theme-btn" data-theme="midnight" style="background:linear-gradient(135deg,#1e293b,#475569);" title="Midnight (Slate)"></button>
            <button class="theme-btn" data-theme="cyber" style="background:linear-gradient(135deg,#00ff41,#003b00);" title="Cyber (Matrix)"></button>
        </div>
        <div class="setting-row" style="margin-top:10px;">
            <span>Autonomy</span>
        </div>
        <div class="mode-tabs" style="margin-bottom:0;margin-top:6px;">
            <button class="mode-tab active autonomy-set" data-autonomy="default" style="flex:1;font-size:11px;padding:5px 8px;">Default</button>
            <button class="mode-tab autonomy-set" data-autonomy="override" style="flex:1;font-size:11px;padding:5px 8px;">Override</button>
            <button class="mode-tab autonomy-set" data-autonomy="autopilot" style="flex:1;font-size:11px;padding:5px 8px;">Autopilot</button>
        </div>
        <div class="setting-row" style="margin-top:10px;">
            <span>Temperature</span>
        </div>
        <div class="temp-row">
            <input type="range" class="temp-slider" id="tempSlider" min="0" max="100" value="70">
            <span class="temp-value" id="tempValue">0.70</span>
        </div>
        <div class="setting-row" style="margin-top:10px;">
            <label>Orchestrator</label>
            <select id="orchestratorSelect">
                <option value="">Auto</option>
                <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                <option value="claude-3-opus-20240229">Claude 3 Opus</option>
                <option value="gpt-4o">GPT-4o</option>
                <option value="gpt-4o-mini">GPT-4o Mini</option>
                <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
            </select>
        </div>
        <div class="setting-row" style="margin-top:6px;">
            <label>Subagent Mode</label>
            <select id="subagentSelect">
                <option value="hybrid">Hybrid</option>
                <option value="cloud">Cloud</option>
                <option value="local">Local</option>
            </select>
        </div>
        <div class="setting-row" style="margin-top:10px;">
            <span>Backend Status</span>
            <span id="backendStatus" style="color:var(--muted);font-size:11px;">Checking...</span>
        </div>
    </div>



    <button class="feature-btn" id="remoteNodesBtn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
        Remote Nodes
    </button>

    <div class="remote-nodes-panel" id="remoteNodesPanel">
        <div class="remote-nodes-header">
            <h2>Mesh Nodes</h2>
            <button class="remote-nodes-refresh" id="discoverNodesBtn">Discover</button>
        </div>
        <div class="empty-nodes" id="remoteNodesEmpty">No remote nodes registered.</div>
        <div id="remoteNodesList"></div>
    </div>

    <button class="feature-btn" id="settingsBtn">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
        Settings
    </button>

    <footer>
        OrbitScribe · Created by ORBSTUDIO
    </footer>

    <div class="toast" id="toast"></div>

    <script nonce="${nonce}">
    (function() {
        'use strict';
        try {
            const vscode = acquireVsCodeApi();

            // Notify extension that webview script is executing
            vscode.postMessage({ command: 'webviewReady' });

            const latestResult = document.getElementById('latestResult');
            const copyBtn = document.getElementById('copyBtn');
            const typeBtn = document.getElementById('typeBtn');
            const clearBtn = document.getElementById('clearBtn');
            const newChatBtn = document.getElementById('newChatBtn');
            const historyBtn = document.getElementById('historyBtn');
            const historyPanel = document.getElementById('historyPanel');
            const historyList = document.getElementById('historyList');
            const historyEmpty = document.getElementById('historyEmpty');
            const ttsBtn = document.getElementById('ttsBtn');
            const settingsBtn = document.getElementById('settingsBtn');
            const settingsPanel = document.getElementById('settingsPanel');
            const backendStatus = document.getElementById('backendStatus');
            const planOptionsBtn = document.getElementById('planOptionsBtn');
            const planOptionsPanel = document.getElementById('planOptionsPanel');
            const planOptionsList = document.getElementById('planOptionsList');
            const planOptionsEmpty = document.getElementById('planOptionsEmpty');
            const remoteNodesBtn = document.getElementById('remoteNodesBtn');
            const remoteNodesPanel = document.getElementById('remoteNodesPanel');
            const remoteNodesList = document.getElementById('remoteNodesList');
            const remoteNodesEmpty = document.getElementById('remoteNodesEmpty');
            const discoverNodesBtn = document.getElementById('discoverNodesBtn');
            const tempSlider = document.getElementById('tempSlider');
            const tempValue = document.getElementById('tempValue');
            const toast = document.getElementById('toast');
            const micBtn = document.getElementById('micBtn');
            const micStatus = document.getElementById('micStatus');
            const chatInput = document.getElementById('chatInput');
            const sendBtn = document.getElementById('sendBtn');
            const orchestratorSelect = document.getElementById('orchestratorSelect');
            const subagentSelect = document.getElementById('subagentSelect');

            let currentText = '';
            let history = [];
            let sessionHistory = [];
            let currentMode = 'ask';
            let currentAutonomy = 'default';
            let currentTemperature = 0.7;
            let currentOrchestrator = '';
            let currentSubagentMode = 'hybrid';
            let isListening = false;
            let pollInterval = null;
            let voiceEngineOnline = false;
            let isStartingEngine = false;
            let isRequestingRecord = false;

            function checkVoiceBackend() {
                vscode.postMessage({ command: 'checkVoiceBackend' });
            }

            function requestStartVoiceBackend() {
                if (isStartingEngine) return;
                isStartingEngine = true;
                if (micStatus) micStatus.textContent = 'Starting engine...';
                vscode.postMessage({ command: 'startVoiceBackend' });
            }

            function startRecording() {
                if (isListening || isRequestingRecord) return;
                isRequestingRecord = true;
                if (micBtn) micBtn.style.pointerEvents = 'none';
                vscode.postMessage({ command: 'startVoiceRecord' });
            }

            function startPolling() {
                if (pollInterval) clearInterval(pollInterval);
                pollInterval = setInterval(() => {
                    vscode.postMessage({ command: 'getVoiceStatus' });
                }, 500);
            }

            function stopPolling() {
                isListening = false;
                if (micBtn) micBtn.classList.remove('listening');
                if (micStatus) micStatus.classList.remove('listening');
                if (micStatus) micStatus.textContent = voiceEngineOnline ? 'Tap to record' : 'Voice engine offline — tap to start';
                if (pollInterval) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                }
            }

            if (micBtn) {
                micBtn.addEventListener('click', () => {
                    if (isListening) {
                        stopPolling();
                        showToast('Recording cancelled');
                    } else if (!voiceEngineOnline) {
                        requestStartVoiceBackend();
                    } else {
                        startRecording();
                    }
                });
            }

            if (tempSlider && tempValue) {
                tempSlider.addEventListener('input', () => {
                    currentTemperature = parseInt(tempSlider.value, 10) / 100;
                    tempValue.textContent = currentTemperature.toFixed(2);
                    try { localStorage.setItem('orbitscribe_temperature', String(currentTemperature)); } catch {}
                });
            }

            if (orchestratorSelect) {
                orchestratorSelect.addEventListener('change', () => {
                    currentOrchestrator = orchestratorSelect.value;
                    try { localStorage.setItem('orbitscribe_orchestrator', currentOrchestrator); } catch {}
                });
            }

            if (subagentSelect) {
                subagentSelect.addEventListener('change', () => {
                    currentSubagentMode = subagentSelect.value;
                    try { localStorage.setItem('orbitscribe_subagent_mode', currentSubagentMode); } catch {}
                });
            }

            document.querySelectorAll('.mode-tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    if (tab.dataset.autonomy) {
                        document.querySelectorAll('.autonomy-set').forEach(t => t.classList.remove('active'));
                        tab.classList.add('active');
                        currentAutonomy = tab.dataset.autonomy;
                        try { localStorage.setItem('orbitscribe_autonomy', currentAutonomy); } catch {}
                        showToast('Autonomy: ' + currentAutonomy);
                        return;
                    }
                    document.querySelectorAll('.mode-tab:not(.autonomy-set)').forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                    currentMode = tab.dataset.mode;
                    showToast('Opening ' + currentMode + ' panel...');
                    if (currentMode === 'swarm') {
                        vscode.postMessage({
                            command: 'openSwarmDeck',
                            mode: currentMode,
                            autonomy: currentAutonomy,
                            temperature: currentTemperature,
                            orchestrator: currentOrchestrator,
                            subagent_mode: currentSubagentMode
                        });
                    } else {
                        vscode.postMessage({
                            command: 'openPanel',
                            mode: currentMode,
                            autonomy: currentAutonomy,
                            temperature: currentTemperature,
                            orchestrator: currentOrchestrator,
                            subagent_mode: currentSubagentMode
                        });
                    }
                });
            });

            function setResult(text) {
                currentText = text;
                if (!latestResult) return;
                if (text) {
                    latestResult.textContent = text;
                    latestResult.classList.remove('empty');
                    if (copyBtn) copyBtn.disabled = false;
                    if (typeBtn) typeBtn.disabled = false;
                    addToHistory(text);
                } else {
                    latestResult.textContent = 'Your transcribed text will appear here...';
                    latestResult.classList.add('empty');
                    if (copyBtn) copyBtn.disabled = true;
                    if (typeBtn) typeBtn.disabled = true;
                }
            }

            async function fetchSessions() {
                try {
                    const controller = new AbortController();
                    const t = setTimeout(() => controller.abort(), 5000);
                    const resp = await fetch('http://127.0.0.1:58081/api/sessions', { signal: controller.signal });
                    clearTimeout(t);
                    if (resp.ok) {
                        const data = await resp.json();
                        sessionHistory = data.sessions || [];
                        renderSessions();
                    } else {
                        sessionHistory = [];
                        renderSessions();
                    }
                } catch (e) {
                    sessionHistory = [];
                    renderSessions();
                }
            }

            function formatDate(iso) {
                if (!iso) return '';
                try {
                    const d = new Date(iso);
                    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
                } catch { return iso; }
            }

            function renderSessions() {
                if (!historyEmpty || !historyList) return;
                if (sessionHistory.length === 0) {
                    historyEmpty.style.display = 'block';
                    historyList.innerHTML = '';
                    return;
                }
                historyEmpty.style.display = 'none';
                historyList.innerHTML = sessionHistory.map((item) => {
                    const sid = escapeHtml(item.session_id || 'unknown');
                    const shortId = sid.length > 12 ? sid.slice(0, 12) + '...' : sid;
                    const meta = formatDate(item.modified_at);
                    return '<div class="history-item">' +
                        '<span class="history-item-text" data-sid="' + sid + '" title="' + sid + '">' + shortId + '</span>' +
                        '<span class="history-item-meta">' + meta + '</span>' +
                        '<button class="history-delete" data-sid="' + sid + '" title="Delete session">×</button>' +
                    '</div>';
                }).join('');
                historyList.querySelectorAll('.history-item-text').forEach(el => {
                    el.addEventListener('click', () => {
                        showToast('Session loaded: ' + el.dataset.sid.slice(0, 8));
                    });
                });
                historyList.querySelectorAll('.history-delete').forEach(el => {
                    el.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        const sid = el.dataset.sid;
                        if (!confirm('Delete session ' + sid.slice(0, 8) + '?')) return;
                        try {
                            const controller = new AbortController();
                            const t = setTimeout(() => controller.abort(), 5000);
                            const resp = await fetch('http://127.0.0.1:58081/api/sessions/' + encodeURIComponent(sid), { method: 'DELETE', signal: controller.signal });
                            clearTimeout(t);
                            if (resp.ok) {
                                showToast('Session deleted');
                                await fetchSessions();
                            } else {
                                showToast('Delete failed');
                            }
                        } catch (err) {
                            showToast('Delete error');
                        }
                    });
                });
            }

            function addToHistory(text) {
                if (!text) return;
                history.unshift({ text, time: new Date().toLocaleTimeString() });
                if (history.length > 20) history.pop();
            }

            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            function showToast(msg) {
                if (!toast) return;
                toast.textContent = msg;
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 2000);
            }

            if (copyBtn) {
                copyBtn.addEventListener('click', () => {
                    if (currentText) {
                        vscode.postMessage({ command: 'copyText', text: currentText });
                    }
                });
            }

            if (typeBtn) {
                typeBtn.addEventListener('click', () => {
                    if (currentText) {
                        vscode.postMessage({ command: 'typeText', text: currentText });
                    }
                });
            }

            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    setResult('');
                    showToast('Cleared');
                });
            }

            if (newChatBtn) {
                newChatBtn.addEventListener('click', () => {
                    vscode.postMessage({ command: 'newChat', mode: currentMode });
                });
            }

            if (historyBtn) {
                historyBtn.addEventListener('click', () => {
                    if (historyPanel) {
                        const wasActive = historyPanel.classList.contains('active');
                        historyPanel.classList.toggle('active');
                        if (!wasActive) {
                            fetchSessions();
                        }
                    }
                });
            }

            if (ttsBtn) {
                ttsBtn.addEventListener('click', () => {
                    if (currentText) {
                        const utterance = new SpeechSynthesisUtterance(currentText);
                        speechSynthesis.speak(utterance);
                        showToast('Speaking...');
                    } else {
                        showToast('No text to speak');
                    }
                });
            }

            if (settingsBtn) {
                settingsBtn.addEventListener('click', () => {
                    if (settingsPanel) settingsPanel.classList.toggle('active');
                });
            }

            if (planOptionsBtn) {
                planOptionsBtn.addEventListener('click', () => {
                    const text = chatInput ? chatInput.value.trim() : '';
                    if (!text) {
                        showToast('Enter a goal first');
                        return;
                    }
                    if (planOptionsPanel) planOptionsPanel.classList.add('active');
                    if (planOptionsEmpty) planOptionsEmpty.textContent = 'Generating approaches...';
                    if (planOptionsList) planOptionsList.innerHTML = '';
                    vscode.postMessage({ command: 'createPlanOptions', goal: text });
                });
            }

            if (remoteNodesBtn) {
                remoteNodesBtn.addEventListener('click', () => {
                    if (remoteNodesPanel) remoteNodesPanel.classList.toggle('active');
                    if (remoteNodesPanel && remoteNodesPanel.classList.contains('active')) {
                        vscode.postMessage({ command: 'getNodes' });
                    }
                });
            }

            if (discoverNodesBtn) {
                discoverNodesBtn.addEventListener('click', () => {
                    if (remoteNodesEmpty) remoteNodesEmpty.textContent = 'Scanning local network...';
                    vscode.postMessage({ command: 'discoverNodes' });
                });
            }

            function renderNodes(nodes) {
                if (!remoteNodesList || !remoteNodesEmpty) return;
                remoteNodesEmpty.style.display = 'none';
                remoteNodesList.innerHTML = '';
                if (!nodes || nodes.length === 0) {
                    remoteNodesEmpty.style.display = 'block';
                    remoteNodesEmpty.textContent = 'No remote nodes registered.';
                    return;
                }
                nodes.forEach((node) => {
                    const div = document.createElement('div');
                    div.className = 'node-item ' + (node.status === 'online' ? 'online' : 'offline');
                    div.innerHTML = '<div class="node-name">' + escapeHtml(node.name || node.node_id) + '</div>' +
                        '<div class="node-meta">' + escapeHtml(node.endpoint || '') + ' · ' + escapeHtml(node.tier || 'shadow') + ' · ' + (node.latency_ms < 9999 ? node.latency_ms + 'ms' : 'offline') + '</div>' +
                        '<div class="node-actions">' +
                            '<button class="node-btn forward" data-node-id="' + escapeHtml(node.node_id) + '">Forward Task</button>' +
                            '<button class="node-btn health-btn" data-node-id="' + escapeHtml(node.node_id) + '">Health</button>' +
                        '</div>';
                    div.querySelector('.forward').addEventListener('click', () => {
                        const text = chatInput ? chatInput.value.trim() : '';
                        if (!text) {
                            showToast('Enter a goal first');
                            return;
                        }
                        vscode.postMessage({ command: 'forwardTask', node_id: node.node_id, goal: text });
                    });
                    div.querySelector('.health-btn').addEventListener('click', () => {
                        vscode.postMessage({ command: 'checkNodeHealth', node_id: node.node_id });
                    });
                    remoteNodesList.appendChild(div);
                });
            }

            function renderPlanOptions(plan) {
                if (!planOptionsList || !planOptionsEmpty) return;
                planOptionsEmpty.style.display = 'none';
                planOptionsList.innerHTML = '';
                if (!plan.options || plan.options.length === 0) {
                    planOptionsEmpty.style.display = 'block';
                    planOptionsEmpty.textContent = 'No options generated.';
                    return;
                }
                plan.options.forEach((opt) => {
                    const div = document.createElement('div');
                    div.className = 'plan-option';
                    div.dataset.optionId = opt.option_id;
                    div.innerHTML = '<div class="plan-option-title">' + escapeHtml(opt.title) + '</div>' +
                        '<div class="plan-option-desc">' + escapeHtml(opt.description) + '</div>' +
                        '<div class="plan-option-meta">' +
                            '<span>' + escapeHtml(opt.complexity) + '</span>' +
                            '<span>' + opt.estimated_files + ' files</span>' +
                            '<span>' + escapeHtml(opt.approach) + '</span>' +
                        '</div>';
                    div.addEventListener('click', () => {
                        document.querySelectorAll('.plan-option').forEach(el => el.classList.remove('selected'));
                        div.classList.add('selected');
                        vscode.postMessage({ command: 'selectPlanOption', plan_id: plan.plan_id, option_id: opt.option_id, goal: plan.goal });
                        showToast('Selected: ' + opt.title);
                        setTimeout(() => {
                            if (planOptionsPanel) planOptionsPanel.classList.remove('active');
                        }, 400);
                    });
                    planOptionsList.appendChild(div);
                });
            }



            const themes = {
                orbit: {
                    '--bg': '#0f1117', '--panel': 'rgba(26, 29, 38, 0.6)', '--panel-solid': '#1a1d26',
                    '--text': '#e2e8f0', '--muted': '#94a3b8', '--accent': '#8b5cf6',
                    '--accent-hover': '#7c3aed', '--accent-light': '#a78bfa', '--accent-dark': '#7c3aed',
                    '--border': 'rgba(45, 49, 66, 0.5)', '--border-solid': '#2d3142'
                },
                neon: {
                    '--bg': '#0a0f14', '--panel': 'rgba(15, 25, 35, 0.6)', '--panel-solid': '#0f1923',
                    '--text': '#e0f2fe', '--muted': '#7dd3fc', '--accent': '#06b6d4',
                    '--accent-hover': '#0891b2', '--accent-light': '#22d3ee', '--accent-dark': '#0e7490',
                    '--border': 'rgba(30, 50, 70, 0.5)', '--border-solid': '#1e3246'
                },
                ember: {
                    '--bg': '#140a0a', '--panel': 'rgba(38, 22, 22, 0.6)', '--panel-solid': '#261616',
                    '--text': '#fef2f2', '--muted': '#fca5a5', '--accent': '#ef4444',
                    '--accent-hover': '#dc2626', '--accent-light': '#f87171', '--accent-dark': '#b91c1c',
                    '--border': 'rgba(66, 35, 35, 0.5)', '--border-solid': '#422323'
                },
                forest: {
                    '--bg': '#0a140a', '--panel': 'rgba(20, 35, 20, 0.6)', '--panel-solid': '#142314',
                    '--text': '#f0fdf4', '--muted': '#86efac', '--accent': '#22c55e',
                    '--accent-hover': '#16a34a', '--accent-light': '#4ade80', '--accent-dark': '#15803d',
                    '--border': 'rgba(30, 55, 30, 0.5)', '--border-solid': '#1e371e'
                },
                sunset: {
                    '--bg': '#1a1010', '--panel': 'rgba(35, 28, 20, 0.6)', '--panel-solid': '#231c14',
                    '--text': '#fffbeb', '--muted': '#fcd34d', '--accent': '#f59e0b',
                    '--accent-hover': '#d97706', '--accent-light': '#fbbf24', '--accent-dark': '#b45309',
                    '--border': 'rgba(60, 50, 35, 0.5)', '--border-solid': '#3c3223'
                },
                midnight: {
                    '--bg': '#020617', '--panel': 'rgba(15, 23, 42, 0.6)', '--panel-solid': '#0f172a',
                    '--text': '#e2e8f0', '--muted': '#94a3b8', '--accent': '#64748b',
                    '--accent-hover': '#475569', '--accent-light': '#cbd5e1', '--accent-dark': '#334155',
                    '--border': 'rgba(30, 41, 59, 0.5)', '--border-solid': '#1e293b'
                },
                cyber: {
                    '--bg': '#000000', '--panel': 'rgba(0, 30, 0, 0.6)', '--panel-solid': '#001a00',
                    '--text': '#00ff41', '--muted': '#008f11', '--accent': '#00ff41',
                    '--accent-hover': '#00cc33', '--accent-light': '#80ff9f', '--accent-dark': '#005500',
                    '--border': 'rgba(0, 80, 0, 0.5)', '--border-solid': '#003b00'
                }
            };

            function applyTheme(name) {
                const t = themes[name];
                if (!t) return;
                const root = document.documentElement;
                Object.entries(t).forEach(([k, v]) => root.style.setProperty(k, v));
                document.querySelectorAll('.theme-btn').forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.theme === name);
                });
                try { localStorage.setItem('orbitscribe_theme', name); } catch {}
            }

            document.querySelectorAll('.theme-btn').forEach(btn => {
                btn.addEventListener('click', () => applyTheme(btn.dataset.theme));
            });

            try {
                const saved = localStorage.getItem('orbitscribe_theme');
                if (saved && themes[saved]) applyTheme(saved);
            } catch {}
            try {
                const savedAutonomy = localStorage.getItem('orbitscribe_autonomy');
                if (savedAutonomy) {
                    currentAutonomy = savedAutonomy;
                    document.querySelectorAll('.autonomy-set').forEach(btn => {
                        btn.classList.toggle('active', btn.dataset.autonomy === currentAutonomy);
                    });
                }
            } catch {}
            try {
                const savedTemp = localStorage.getItem('orbitscribe_temperature');
                if (savedTemp && tempSlider && tempValue) {
                    currentTemperature = parseFloat(savedTemp);
                    tempSlider.value = Math.round(currentTemperature * 100);
                    tempValue.textContent = currentTemperature.toFixed(2);
                }
            } catch {}
            try {
                const savedOrchestrator = localStorage.getItem('orbitscribe_orchestrator');
                if (savedOrchestrator && orchestratorSelect) {
                    currentOrchestrator = savedOrchestrator;
                    orchestratorSelect.value = currentOrchestrator;
                }
            } catch {}
            try {
                const savedSubagent = localStorage.getItem('orbitscribe_subagent_mode');
                if (savedSubagent && subagentSelect) {
                    currentSubagentMode = savedSubagent;
                    subagentSelect.value = currentSubagentMode;
                }
            } catch {}

            async function updateBackendStatus() {
                if (!backendStatus) return;
                try {
                    const controller = new AbortController();
                    const t = setTimeout(() => controller.abort(), 5000);
                    const resp = await fetch('http://127.0.0.1:58081/api/health', { method: 'GET', signal: controller.signal });
                    clearTimeout(t);
                    if (resp.ok) {
                        backendStatus.textContent = 'Online';
                        backendStatus.style.color = '#22c55e';
                    } else {
                        backendStatus.textContent = 'Error';
                        backendStatus.style.color = '#ef4444';
                    }
                } catch {
                    backendStatus.textContent = 'Offline';
                    backendStatus.style.color = '#ef4444';
                }
            }
            updateBackendStatus();
            setInterval(updateBackendStatus, 10000);

            function sendMessage() {
                const text = chatInput ? chatInput.value.trim() : '';
                if (!text) return;
                if (chatInput) chatInput.value = '';
                setResult(text);
                vscode.postMessage({ command: 'sendMessage', text: text, mode: currentMode, temperature: currentTemperature });
            }

            if (sendBtn) {
                sendBtn.addEventListener('click', sendMessage);
            }
            if (chatInput) {
                chatInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                    }
                });
            }

            window.addEventListener('message', (e) => {
                try {
                    const msg = e.data;
                    switch (msg.command) {
                        case 'setResult':
                            setResult(msg.text);
                            break;
                        case 'toast':
                            showToast(msg.message);
                            break;
                        case 'voiceBackendStatus':
                            voiceEngineOnline = msg.ok;
                            if (micStatus) {
                                micStatus.textContent = msg.ok ? 'Tap to record' : 'Voice engine offline — tap to start';
                            }
                            break;
                        case 'backendStatus': {
                            const enginePill = document.getElementById('enginePill');
                            const engineLabel = document.getElementById('engineLabel');
                            const ollamaPill = document.getElementById('ollamaPill');
                            const ollamaLabel = document.getElementById('ollamaLabel');
                            const modelPill = document.getElementById('modelPill');
                            const modelLabel = document.getElementById('modelLabel');

                            if (enginePill) {
                                enginePill.classList.toggle('online', msg.online);
                                enginePill.classList.toggle('offline', !msg.online);
                                if (engineLabel) engineLabel.textContent = msg.online ? 'Engine: Online' : 'Engine: Offline';
                            }
                            if (ollamaPill) {
                                ollamaPill.classList.toggle('online', msg.ollama);
                                ollamaPill.classList.toggle('offline', !msg.ollama);
                                if (ollamaLabel) ollamaLabel.textContent = msg.ollama ? 'Ollama: Online' : 'Ollama: Offline';
                            }
                            if (modelPill) {
                                const modelName = msg.model && msg.model !== 'unknown' ? msg.model : 'No model';
                                modelPill.classList.toggle('online', msg.online && msg.model !== 'unknown');
                                modelPill.classList.toggle('offline', !msg.online || msg.model === 'unknown');
                                if (modelLabel) modelLabel.textContent = 'Model: ' + modelName;
                            }
                            break;
                        }
                        case 'voiceBackendStarted':
                            isStartingEngine = false;
                            if (msg.ok) {
                                voiceEngineOnline = true;
                                if (micStatus) micStatus.textContent = 'Tap to record';
                                showToast('Voice engine started');
                            } else {
                                if (micStatus) micStatus.textContent = 'Voice engine offline — tap to start';
                                showToast(msg.error || 'Failed to start voice engine');
                            }
                            break;
                        case 'voiceRecordStarted':
                            isRequestingRecord = false;
                            if (micBtn) micBtn.style.pointerEvents = '';
                            if (msg.ok) {
                                isListening = true;
                                if (micBtn) micBtn.classList.add('listening');
                                if (micStatus) {
                                    micStatus.textContent = 'Listening...';
                                    micStatus.classList.add('listening');
                                }
                                startPolling();
                            } else if (msg.error === 'Voice engine not reachable') {
                                voiceEngineOnline = false;
                                if (micStatus) micStatus.textContent = 'Voice engine offline — tap to start';
                                showToast('Voice engine offline — tap mic to start');
                            } else if (msg.error === 'Already recording') {
                                showToast('Already recording — please wait');
                            } else {
                                if (micStatus) micStatus.textContent = msg.error || 'Could not start';
                                showToast(msg.error || 'Could not start recording');
                            }
                            break;
                        case 'voiceStatusUpdate':
                            if (msg.status === 'listening') {
                                if (micStatus) micStatus.textContent = 'Listening...';
                            } else if (msg.status === 'processing') {
                                if (micStatus) micStatus.textContent = 'Processing...';
                            } else if (msg.status === 'result' && msg.message) {
                                stopPolling();
                                setResult(msg.message);
                                showToast('Transcribed');
                            } else if (msg.status === 'error') {
                                stopPolling();
                                if (micStatus) micStatus.textContent = 'Error';
                                showToast(msg.message || 'Recording error');
                            } else if (msg.status === 'idle') {
                                stopPolling();
                                if (micStatus) micStatus.textContent = voiceEngineOnline ? 'Tap to record' : 'Voice engine offline — tap to start';
                                if (!msg.message) {
                                    showToast('No speech detected');
                                }
                            } else if (msg.status === 'offline') {
                                stopPolling();
                                if (micStatus) micStatus.textContent = 'Voice engine offline';
                            }
                            break;
                        case 'planOptionsCreated':
                            if (msg.success && msg.plan) {
                                renderPlanOptions(msg.plan);
                                showToast('Generated ' + msg.plan.options.length + ' approaches');
                            } else {
                                if (planOptionsEmpty) {
                                    planOptionsEmpty.style.display = 'block';
                                    planOptionsEmpty.textContent = msg.error || 'Failed to generate options';
                                }
                            }
                            break;
                        case 'planOptionSelected':
                            if (msg.success) {
                                showToast('Opening plan panel...');
                            } else {
                                showToast(msg.error || 'Failed to select option');
                            }
                            break;
                        case 'nodesList':
                            renderNodes(msg.nodes);
                            break;
                        case 'nodesDiscovered':
                            if (msg.success) {
                                renderNodes(msg.nodes);
                                showToast('Discovered ' + msg.discovered + ' nodes');
                            } else {
                                showToast(msg.error || 'Discovery failed');
                            }
                            break;
                        case 'taskForwarded':
                            if (msg.success) {
                                showToast('Task forwarded to ' + (msg.node_id || 'remote node'));
                            } else {
                                showToast(msg.error || 'Forward failed');
                            }
                            break;
                        case 'nodeHealth':
                            showToast((msg.node_id || 'Node') + ' is ' + (msg.healthy ? 'healthy' : 'unreachable'));
                            break;
                    }
                } catch (handlerErr) {
                    console.error('[OrbitScribe Webview] Message handler error:', handlerErr);
                }
            });

            if (copyBtn) copyBtn.disabled = true;
            if (typeBtn) typeBtn.disabled = true;
            checkVoiceBackend();
        } catch (initErr) {
            console.error('[OrbitScribe Webview] FATAL INIT ERROR:', initErr);
            document.body.innerHTML = '<div style="padding:20px;color:#ef4444;font-family:sans-serif;">OrbitScribe failed to load.<br><small>' + (initErr && initErr.message || initErr) + '</small></div>';
        }
    })();
    </script>
</body>
</html>`;
    }
}

function getNonce(): string {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

function getFallbackHtml(): string {
    return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>OrbitScribe</title></head>
<body style="font-family:sans-serif;padding:20px;background:#0f1117;color:#e2e8f0;">
    <h2>OrbitScribe</h2>
    <p style="color:#94a3b8;">The sidebar could not be loaded. Please reload the window.</p>
</body>
</html>`;
}
