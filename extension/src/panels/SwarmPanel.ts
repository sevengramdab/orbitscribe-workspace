import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { JukeboxPanel } from './JukeboxPanel';

export class SwarmPanel {
    public static currentPanel: SwarmPanel | undefined;
    public static readonly viewType = 'orbitscribe.swarmPanel';
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;

    public static createOrShow(extensionUri: vscode.Uri, initialMode?: string) {
        const column = vscode.ViewColumn.Beside;

        if (SwarmPanel.currentPanel) {
            SwarmPanel.currentPanel._panel.reveal(column);
            if (initialMode) {
                SwarmPanel.currentPanel.sendMessage({ command: 'setMode', mode: initialMode });
            }
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            SwarmPanel.viewType,
            'OrbitScribe',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri],
            }
        );

        SwarmPanel.currentPanel = new SwarmPanel(panel, extensionUri, initialMode);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, initialMode?: string) {
        this._panel = panel;
        this._extensionUri = extensionUri;
        this._panel.webview.html = SwarmPanel.getHtml(this._panel.webview, extensionUri, initialMode);

        this._panel.onDidDispose(() => {
            SwarmPanel.currentPanel = undefined;
        });

        this._panel.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case 'getWorkspaceContext': {
                    const ctx = await (await import('../extension')).getWorkspaceContext();
                    const folders = vscode.workspace.workspaceFolders;
                    const workspaceRoot = folders?.[0]?.uri?.fsPath ?? '';
                    this._panel.webview.postMessage({ command: 'workspaceContext', context: ctx, workspaceRoot });
                    break;
                }
                case 'newChat': {
                    this._panel.webview.postMessage({ command: 'resetChat' });
                    break;
                }
                case 'sessionStarted': {
                    // Forward session ID to Command Viewport for dashboard sync
                    const { CommandViewport } = await import('./CommandViewport');
                    if (CommandViewport.currentPanel && message.session_id) {
                        CommandViewport.currentPanel.sendMessage({ command: 'setSession', sessionId: message.session_id });
                    }
                    // Persist session ID for auto-resume across reloads
                    if (message.session_id) {
                        try {
                            const folders = vscode.workspace.workspaceFolders;
                            const workspaceRoot = folders?.[0]?.uri?.fsPath ?? '';
                            const toolsDir = workspaceRoot ? path.join(workspaceRoot, 'tools') : '';
                            if (toolsDir) {
                                fs.writeFileSync(path.join(toolsDir, '.kimi-last-session'), message.session_id);
                            }
                        } catch (e) {
                            console.error('[SwarmPanel] Failed to persist session ID:', e);
                        }
                    }
                    break;
                }
                case 'triggerVoice': {
                    this._panel.webview.postMessage({ command: 'triggerVoice' });
                    break;
                }
                case 'executeTool': {
                    const { tool, args, request_id } = message;
                    try {
                        const result = await executeTool(tool, args);
                        this._panel.webview.postMessage({
                            command: 'toolExecuted',
                            request_id,
                            result: {
                                tool,
                                args: args || {},
                                status: result.status,
                                data: result.data ?? null,
                                error: result.error || ''
                            }
                        });
                    } catch (err: any) {
                        this._panel.webview.postMessage({
                            command: 'toolExecuted',
                            request_id,
                            result: {
                                tool,
                                args: args || {},
                                status: 'error',
                                data: null,
                                error: err.message || String(err)
                            }
                        });
                    }
                    break;
                }
                case 'sendApproval': {
                    try {
                        const { httpPost } = await import('../services/httpUtil');
                        await httpPost(`http://127.0.0.1:58081/api/approval/respond`, {
                            session_id: message.session_id,
                            request_id: message.request_id,
                            approved: message.approved,
                        });
                    } catch (err: any) {
                        console.error('sendApproval failed:', err);
                    }
                    break;
                }
                case 'sendDecision': {
                    try {
                        const { httpPost } = await import('../services/httpUtil');
                        await httpPost(`http://127.0.0.1:58081/api/decision/respond`, {
                            session_id: message.session_id,
                            request_id: message.request_id,
                            decision: message.decision,
                        });
                    } catch (err: any) {
                        console.error('sendDecision failed:', err);
                    }
                    break;
                }
                case 'showDiff': {
                    try {
                        const folders = vscode.workspace.workspaceFolders;
                        const workspaceRoot = folders?.[0]?.uri?.fsPath ?? '';
                        let filePath = message.file_path || '';
                        if (workspaceRoot && filePath && !path.isAbsolute(filePath)) {
                            filePath = path.join(workspaceRoot, filePath);
                        }
                        if (filePath && fs.existsSync(filePath)) {
                            const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(filePath));
                            await vscode.window.showTextDocument(doc);
                        } else {
                            vscode.window.showWarningMessage(`⚠️ File not found: ${message.file_path}`);
                        }
                    } catch (err: any) {
                        console.error('showDiff failed:', err);
                        vscode.window.showErrorMessage(`❌ Could not open file: ${err.message || err}`);
                    }
                    break;
                }
                case 'applyBatch': {
                    try {
                        const { httpPost } = await import('../services/httpUtil');
                        await httpPost(`http://127.0.0.1:58081/api/batches/${message.batch_id}/apply`);
                    } catch (err: any) {
                        console.error('applyBatch failed:', err);
                    }
                    break;
                }
                case 'undoBatch': {
                    try {
                        const { httpPost } = await import('../services/httpUtil');
                        await httpPost(`http://127.0.0.1:58081/api/batches/${message.batch_id}/undo`);
                    } catch (err: any) {
                        console.error('undoBatch failed:', err);
                    }
                    break;
                }
                case 'stopSession': {
                    try {
                        // Abort the stream on the backend by sending a steering command
                        const { httpPost } = await import('../services/httpUtil');
                        await httpPost(`http://127.0.0.1:58081/api/steer`, {
                            session_id: message.session_id,
                            command: 'stop',
                        });
                    } catch (err: any) {
                        console.error('stopSession failed:', err);
                    }
                    break;
                }
                case 'saveSession': {
                    try {
                        const { httpPost } = await import('../services/httpUtil');
                        const res = await httpPost(`http://127.0.0.1:58081/api/sessions/${message.session_id}/save`);
                        if (res.ok) {
                            this._panel.webview.postMessage({ command: 'sessionSaved', session_id: message.session_id });
                        } else {
                            this._panel.webview.postMessage({ command: 'sessionSaveError', session_id: message.session_id, error: `HTTP ${res.status}` });
                        }
                    } catch (err: any) {
                        console.error('saveSession failed:', err);
                        this._panel.webview.postMessage({ command: 'sessionSaveError', session_id: message.session_id, error: err.message || String(err) });
                    }
                    break;
                }
                case 'deleteSession': {
                    try {
                        const { httpDelete } = await import('../services/httpUtil');
                        const res = await httpDelete(`http://127.0.0.1:58081/api/sessions/${message.session_id}`);
                        if (res.ok) {
                            this._panel.webview.postMessage({ command: 'sessionDeleted', session_id: message.session_id });
                        } else {
                            this._panel.webview.postMessage({ command: 'sessionDeleteError', session_id: message.session_id, error: `HTTP ${res.status}` });
                        }
                    } catch (err: any) {
                        console.error('deleteSession failed:', err);
                        this._panel.webview.postMessage({ command: 'sessionDeleteError', session_id: message.session_id, error: err.message || String(err) });
                    }
                    break;
                }
                case 'openJukebox': {
                    JukeboxPanel.createOrShow(this._extensionUri);
                    break;
                }
            }
        });
    }

    sendMessage(message: any) {
        this._panel.webview.postMessage(message);
    }

    reveal() {
        this._panel.reveal(vscode.ViewColumn.Beside);
    }

    public static getHtml(webview: vscode.Webview, extensionUri: vscode.Uri, initialMode?: string): string {
        const mode = initialMode || 'auto';
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'out', 'panels', 'swarm-panel-webview.js'));

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline' ${webview.cspSource}; script-src 'self' ${webview.cspSource}; connect-src http://127.0.0.1:*;">
    <title>OrbitScribe</title>
    <style>
        :root {
            --bg: #0f1117;
            --panel: #1a1d26;
            --text: #e2e8f0;
            --muted: #94a3b8;
            --accent: #8b5cf6;
            --accent-hover: #7c3aed;
            --border: #2d3142;
            --success: #22c55e;
            --warning: #f59e0b;
            --error: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Segoe UI', system-ui, sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .header h1 {
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.05em;
        }
        .settings-row {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 12px;
            border-bottom: 1px solid var(--border);
            flex-wrap: wrap;
        }
        .settings-row label {
            font-size: 11px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .settings-row select {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text);
            padding: 4px 8px;
            font-size: 12px;
            outline: none;
        }
        .settings-row input[type="range"] {
            flex: 1;
            max-width: 120px;
        }
        .settings-row span {
            font-size: 12px;
            color: var(--muted);
            min-width: 32px;
        }
        .token-meter {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 11px;
            color: var(--muted);
            margin-left: auto;
        }
        .token-meter .bar {
            width: 60px;
            height: 6px;
            background: var(--border);
            border-radius: 3px;
            overflow: hidden;
        }
        .token-meter .bar-fill {
            height: 100%;
            background: var(--accent);
            width: 0%;
            transition: width 0.3s;
        }
        .autonomy-tabs {
            display: flex;
            gap: 4px;
            padding: 6px 12px;
            border-bottom: 1px solid var(--border);
        }
        .autonomy-btn {
            padding: 5px 10px;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: transparent;
            color: var(--muted);
            font-size: 11px;
            cursor: pointer;
            transition: all 0.15s;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        .autonomy-btn:hover { color: var(--text); border-color: var(--accent); }
        .autonomy-btn.active {
            background: var(--accent);
            color: #fff;
            border-color: var(--accent);
        }
        .mode-tabs {
            display: flex;
            gap: 4px;
            padding: 8px 12px;
            border-bottom: 1px solid var(--border);
        }
        .mode-tab {
            padding: 6px 12px;
            border-radius: 6px;
            border: none;
            background: transparent;
            color: var(--muted);
            font-size: 12px;
            cursor: pointer;
            transition: all 0.15s;
        }
        .mode-tab:hover { color: var(--text); }
        .mode-tab.active {
            background: var(--accent);
            color: #fff;
        }
        .chat-area {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .message {
            max-width: 90%;
            padding: 10px 14px;
            border-radius: 12px;
            font-size: 13px;
            line-height: 1.5;
            word-break: break-word;
        }
        .message.user {
            align-self: flex-end;
            background: var(--accent);
            color: #fff;
        }
        .message.assistant {
            align-self: flex-start;
            background: var(--panel);
            border: 1px solid var(--border);
        }
        .message.system {
            align-self: center;
            background: transparent;
            color: var(--muted);
            font-size: 12px;
            font-style: italic;
        }
        .message .agent-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--accent);
            margin-bottom: 4px;
            font-weight: 600;
        }
        .approval-card, .decision-card, .batch-review-card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px;
            max-width: 95%;
            align-self: flex-start;
        }
        .card-title {
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 8px;
            color: var(--text);
        }
        .card-actions {
            display: flex;
            gap: 8px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        .card-btn {
            padding: 6px 14px;
            border-radius: 8px;
            border: none;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.15s;
            font-weight: 600;
        }
        .card-btn.approve {
            background: var(--success);
            color: #fff;
        }
        .card-btn.approve:hover { background: #16a34a; }
        .card-btn.reject {
            background: var(--error);
            color: #fff;
        }
        .card-btn.reject:hover { background: #dc2626; }
        .card-btn.decision {
            background: var(--accent);
            color: #fff;
        }
        .card-btn.decision:hover { background: var(--accent-hover); }
        .card-btn.secondary {
            background: var(--panel);
            border: 1px solid var(--border);
            color: var(--text);
        }
        .card-btn.secondary:hover { border-color: var(--accent); }
        .card-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .batch-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        .batch-file-item {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px solid var(--border);
            font-size: 12px;
        }
        .batch-file-item.active {
            background: rgba(139, 92, 246, 0.1);
        }
        .batch-file-name { color: var(--text); }
        .batch-file-status { font-size: 10px; text-transform: uppercase; font-weight: 600; }
        .batch-file-status.pending { color: var(--muted); }
        .batch-file-status.approved { color: var(--success); }
        .batch-file-status.rejected { color: var(--error); }
        .batch-nav { display: flex; gap: 8px; margin: 8px 0; }
        .batch-nav-btn {
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: var(--panel);
            color: var(--text);
            font-size: 11px;
            cursor: pointer;
        }
        .batch-nav-btn:hover { border-color: var(--accent); }
        .batch-actions { display: flex; gap: 6px; margin-top: 10px; flex-wrap: wrap; }
        .input-area {
            padding: 12px;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 8px;
        }
        .chat-input {
            flex: 1;
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px 14px;
            color: var(--text);
            font-size: 13px;
            resize: none;
            outline: none;
            font-family: inherit;
        }
        .chat-input:focus { border-color: var(--accent); }
        .send-btn, .voice-btn, .tts-btn {
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
            font-size: 14px;
        }
        .send-btn:hover, .voice-btn:hover, .tts-btn:hover { background: var(--accent-hover); }
        .voice-btn {
            background: var(--panel);
            border: 1px solid var(--border);
        }
        .tts-btn {
            background: var(--panel);
            border: 1px solid var(--border);
        }
        .tts-btn.speaking {
            background: var(--error);
            border-color: var(--error);
            animation: pulse 1.2s infinite;
        }
        .status-bar {
            padding: 6px 12px;
            font-size: 11px;
            color: var(--muted);
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
        }
        .api-badge {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .api-badge.local { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
        .api-badge.cloud { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
        .api-badge.hybrid { background: rgba(139, 92, 246, 0.15); color: #a78bfa; }
        .api-badge.locked { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
        .loading { animation: pulse 1.5s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .init-banner {
            position: fixed;
            bottom: 60px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--panel);
            border: 1px solid var(--border);
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 12px;
            color: var(--muted);
            z-index: 100;
        }
        .session-toolbar {
            display: flex;
            gap: 8px;
            padding: 6px 12px;
            border-bottom: 1px solid var(--border);
            align-items: center;
            background: var(--panel);
        }
        .toolbar-btn {
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid var(--border);
            background: transparent;
            color: var(--muted);
            font-size: 11px;
            cursor: pointer;
            transition: all 0.15s;
            font-weight: 600;
        }
        .toolbar-btn:hover {
            border-color: var(--accent);
            color: var(--text);
        }
        .toolbar-btn.stop { border-color: rgba(239, 68, 68, 0.3); color: #f87171; }
        .toolbar-btn.stop:hover { background: rgba(239, 68, 68, 0.1); }
        .toolbar-btn.save { border-color: rgba(34, 197, 94, 0.3); color: #4ade80; }
        .toolbar-btn.save:hover { background: rgba(34, 197, 94, 0.1); }
        .toolbar-btn.delete { border-color: rgba(239, 68, 68, 0.3); color: #f87171; }
        .toolbar-btn.delete:hover { background: rgba(239, 68, 68, 0.1); }
        .session-id-display {
            margin-left: auto;
            font-size: 10px;
            color: var(--muted);
            font-family: var(--font-mono);
        }
    </style>
</head>
<body data-mode="${mode}">
    <div class="header">
        <h1>🐝 ORBITSCRIBE</h1>
    </div>
    <div class="session-toolbar">
        <button class="toolbar-btn stop" id="stopSessionBtn" title="Stop current run">⏹ Stop</button>
        <button class="toolbar-btn save" id="saveSessionBtn" title="Save session">💾 Save</button>
        <button class="toolbar-btn delete" id="deleteSessionBtn" title="Delete session">🗑️ Delete</button>
        <button class="toolbar-btn" id="jukeboxBtn" title="Open Infinite Jukebox" style="margin-left:auto;border-color:#00f0ff;color:#00f0ff">🎵 Jukebox</button>
        <span class="session-id-display" id="sessionIdDisplay"></span>
    </div>
    <div class="settings-row">
        <label>Auto</label>
        <select id="modelSelect"><option value="">Auto</option></select>
        <label>Temp</label>
        <input type="range" id="tempSlider" min="0" max="100" value="70">
        <span id="tempValue">0.70</span>
        <label>Speed</label>
        <input type="range" id="ttsSpeedSlider" min="50" max="200" value="150">
        <span id="ttsSpeedValue">150</span>
        <div class="token-meter" id="tokenMeter" title="Token usage estimate">
            <span id="tokenText">0 ↑ 0 ↓</span>
            <div class="bar"><div class="bar-fill" id="tokenBar"></div></div>
        </div>
    </div>
    <div class="settings-row" id="swarmSettings" style="display:none;">
        <label>Orchestrator</label>
        <select id="orchestratorSelect"><option value="">Auto</option></select>
        <label>Subagents</label>
        <select id="subagentSelect">
            <option value="hybrid">Hybrid</option>
            <option value="cloud">Cloud</option>
            <option value="local">Local</option>
        </select>
    </div>
    <div class="autonomy-tabs">
        <button class="autonomy-btn active" data-level="default">Default</button>
        <button class="autonomy-btn" data-level="override">Override</button>
        <button class="autonomy-btn" data-level="autopilot">Autopilot</button>
    </div>
    <div class="mode-tabs">
        <button class="mode-tab ${mode === 'auto' ? 'active' : ''}" data-mode="auto">Auto</button>
        <button class="mode-tab ${mode === 'ask' ? 'active' : ''}" data-mode="ask">Ask</button>
        <button class="mode-tab ${mode === 'plan' ? 'active' : ''}" data-mode="plan">Plan</button>
        <button class="mode-tab ${mode === 'agent' ? 'active' : ''}" data-mode="agent">Agent</button>
        <button class="mode-tab ${mode === 'swarm' ? 'active' : ''}" data-mode="swarm">Swarm</button>
    </div>
    <div class="chat-area" id="chatArea"></div>
    <div class="input-area">
        <textarea class="chat-input" id="chatInput" rows="2" placeholder="Ask, plan, or delegate..."></textarea>
        <button class="voice-btn" id="voiceBtn" title="Voice input (requires OrbitScribe)">🎤</button>
        <button class="tts-btn" id="ttsBtn" title="Read last output">🔊</button>
        <button class="send-btn" id="sendBtn">➤</button>
    </div>
    <div class="status-bar">
        <span id="statusText">Ready</span>
        <span class="api-badge local" id="apiBadge">Auto</span>
    </div>
    <div class="init-banner" id="initBanner">Initializing OrbitScribe...</div>

    <script src="${scriptUri}"></script>
</body>
</html>`;
    }
}

async function executeTool(tool: string, args: any): Promise<{ status: string; data?: any; error?: string }> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    const workspaceRoot = workspaceFolders?.[0]?.uri;

    switch (tool) {
        case 'read_file': {
            const filePath = args?.path;
            if (!filePath) { throw new Error('read_file requires "path" argument'); }
            const uri = workspaceRoot
                ? vscode.Uri.joinPath(workspaceRoot, filePath)
                : vscode.Uri.file(filePath);
            const data = await vscode.workspace.fs.readFile(uri);
            const content = Buffer.from(data).toString('utf-8');
            return { status: 'ok', data: { content } };
        }
        case 'write_file': {
            const filePath = args?.path;
            const content = args?.content ?? '';
            if (!filePath) { throw new Error('write_file requires "path" argument'); }
            const uri = workspaceRoot
                ? vscode.Uri.joinPath(workspaceRoot, filePath)
                : vscode.Uri.file(filePath);
            await vscode.workspace.fs.writeFile(uri, Buffer.from(content, 'utf-8'));
            return { status: 'ok', data: { path: filePath } };
        }
        case 'list_files': {
            const dirPath = args?.path || '.';
            const uri = workspaceRoot
                ? vscode.Uri.joinPath(workspaceRoot, dirPath)
                : vscode.Uri.file(dirPath);
            const entries = await vscode.workspace.fs.readDirectory(uri);
            const files = entries.map(([name, type]) => ({
                name,
                type: type === vscode.FileType.Directory ? 'directory' : 'file'
            }));
            return { status: 'ok', data: { files } };
        }
        case 'run_command': {
            const command = args?.command;
            if (!command) { throw new Error('run_command requires "command" argument'); }
            const { exec } = require('child_process');
            const { promisify } = require('util');
            const execAsync = promisify(exec);
            const cwd = workspaceRoot ? workspaceRoot.fsPath : undefined;
            try {
                const { stdout, stderr } = await execAsync(command, { cwd, timeout: 30000 });
                return { status: 'ok', data: { stdout, stderr, code: 0 } };
            } catch (execError: any) {
                return {
                    status: 'error',
                    data: {
                        stdout: execError.stdout || '',
                        stderr: execError.stderr || '',
                        code: execError.code ?? execError.status ?? -1
                    },
                    error: execError.message || 'Command failed'
                };
            }
        }
        case 'search_files': {
            const query = args?.query;
            if (!query) { throw new Error('search_files requires "query" argument'); }
            const pattern = query.includes('*') ? query : `**/*${query}*`;
            const files = await vscode.workspace.findFiles(pattern, '**/node_modules/**');
            return { status: 'ok', data: { files: files.map(f => vscode.workspace.asRelativePath(f)) } };
        }
        case 'get_current_weather':
        case 'get_time_at_location': {
            return { status: 'error', error: `${tool} is not implemented in the extension. Use file tools instead.` };
        }
        default:
            throw new Error(`Unknown tool: ${tool}`);
    }
}

function getNonce() {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}
