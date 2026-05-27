import * as vscode from 'vscode';

export class CommandViewport {
    public static currentPanel: CommandViewport | undefined;
    public static readonly viewType = 'orbitscribe.commandViewport';
    private readonly _panel: vscode.WebviewPanel;

    public static createOrShow(extensionUri: vscode.Uri, sessionId?: string) {
        const column = vscode.ViewColumn.Beside;

        if (CommandViewport.currentPanel) {
            CommandViewport.currentPanel._panel.reveal(column);
            if (sessionId) {
                CommandViewport.currentPanel.sendMessage({ command: 'setSession', sessionId });
            }
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            CommandViewport.viewType,
            '🛰️ Command Viewport',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri],
            }
        );

        CommandViewport.currentPanel = new CommandViewport(panel, extensionUri, sessionId);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri, sessionId?: string) {
        this._panel = panel;
        this._panel.webview.html = CommandViewport.getHtml(this._panel.webview, extensionUri, sessionId);

        this._panel.onDidDispose(() => {
            CommandViewport.currentPanel = undefined;
        });

        this._panel.webview.onDidReceiveMessage(async (message) => {
            const port = vscode.workspace.getConfiguration('orbitscribe').get<number>('backendPort', 58081);
            switch (message.command) {
                case 'getWorkspaceContext': {
                    const ctx = await (await import('../extension')).getWorkspaceContext();
                    this._panel.webview.postMessage({ command: 'workspaceContext', context: ctx });
                    break;
                }
                case 'executeTool': {
                    const { tool, args, request_id } = message;
                    try {
                        const { executeTool } = await import('../extension');
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
                case 'steerAgent': {
                    try {
                        const { httpPost } = await import('../services/httpUtil');
                        await httpPost(`http://127.0.0.1:${port}/api/agents/${message.agent_id}/steer`, {
                            message: message.message,
                        });
                    } catch (err: any) {
                        console.error('steerAgent failed:', err);
                    }
                    break;
                }
                case 'sendApproval': {
                    try {
                        const { httpPost } = await import('../services/httpUtil');
                        await httpPost(`http://127.0.0.1:${port}/api/approval/respond`, {
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
                        await httpPost(`http://127.0.0.1:${port}/api/decision/respond`, {
                            session_id: message.session_id,
                            request_id: message.request_id,
                            decision: message.decision,
                        });
                    } catch (err: any) {
                        console.error('sendDecision failed:', err);
                    }
                    break;
                }
            }
        });
    }

    sendMessage(message: any) {
        this._panel.webview.postMessage(message);
    }

    public static getHtml(webview: vscode.Webview, extensionUri: vscode.Uri, sessionId?: string): string {
        const sid = sessionId || '';
        const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(extensionUri, 'out', 'panels', 'command-viewport-webview.js'));

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline' ${webview.cspSource}; script-src 'self' ${webview.cspSource}; connect-src http://127.0.0.1:* ws://127.0.0.1:*;">
    <title>Command Viewport</title>
    <style>
        :root {
            --bg: #0a0c10;
            --panel: #11141c;
            --text: #e2e8f0;
            --muted: #64748b;
            --accent: #00d4ff;
            --accent2: #8b5cf6;
            --border: #1e2230;
            --success: #22c55e;
            --warning: #f59e0b;
            --error: #ef4444;
            --idle: #3b82f6;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Segoe UI', system-ui, sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .header {
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--panel);
        }
        .header h1 {
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--accent);
        }
        .header .session-id {
            font-size: 10px;
            color: var(--muted);
            font-family: 'Fira Code', monospace;
        }
        .main {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
        .tree-pane {
            width: 280px;
            min-width: 200px;
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            background: var(--bg);
        }
        .tree-header {
            padding: 8px 12px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--muted);
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .tree-filter {
            display: flex;
            gap: 4px;
            padding: 6px 10px;
            border-bottom: 1px solid var(--border);
        }
        .tree-filter button {
            font-size: 10px;
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid var(--border);
            background: transparent;
            color: var(--muted);
            cursor: pointer;
        }
        .tree-filter button.active {
            background: var(--accent);
            color: #000;
            border-color: var(--accent);
        }
        .tree-scroll {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }
        .tree-node {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 4px 0;
            cursor: pointer;
            border-radius: 4px;
            padding-left: 4px;
        }
        .tree-node:hover {
            background: rgba(0,212,255,0.05);
        }
        .tree-node.selected {
            background: rgba(0,212,255,0.1);
            border-left: 2px solid var(--accent);
        }
        .tree-children {
            padding-left: 16px;
            border-left: 1px dashed var(--border);
            margin-left: 6px;
        }
        .tree-chevron {
            font-size: 10px;
            color: var(--muted);
            width: 12px;
            text-align: center;
            cursor: pointer;
        }
        .tree-chevron.collapsed::before { content: '▶'; }
        .tree-chevron.expanded::before { content: '▼'; }
        .tree-chevron.leaf::before { content: ''; }
        .led {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        .led.active {
            background: var(--success);
            box-shadow: 0 0 8px var(--success);
            animation: pulse 1.2s infinite;
        }
        .led.idle {
            background: var(--idle);
            box-shadow: 0 0 4px var(--idle);
        }
        .led.paused {
            background: var(--warning);
            box-shadow: 0 0 4px var(--warning);
        }
        .led.error {
            background: var(--error);
            box-shadow: 0 0 8px var(--error);
            animation: flash 0.6s infinite;
        }
        .led.queued {
            background: var(--muted);
            box-shadow: none;
        }
        .led.committed {
            background: var(--accent2);
            box-shadow: 0 0 4px var(--accent2);
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        @keyframes flash {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.2; }
        }
        .tree-label {
            font-size: 12px;
            color: var(--text);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .tree-role {
            font-size: 9px;
            text-transform: uppercase;
            color: var(--muted);
            margin-left: auto;
            padding-left: 6px;
        }
        .viewport-pane {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: var(--bg);
        }
        .viewport-header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 10px;
            background: var(--panel);
        }
        .viewport-header .led {
            width: 12px;
            height: 12px;
        }
        .viewport-header .agent-name {
            font-size: 16px;
            font-weight: 700;
        }
        .viewport-header .agent-status {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 2px 8px;
            border-radius: 4px;
            background: var(--border);
            color: var(--muted);
        }
        .viewport-body {
            flex: 1;
            overflow-y: auto;
            padding: 12px 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .section-card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }
        .section-header {
            padding: 10px 14px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--accent);
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .section-header::after {
            content: '▼';
            font-size: 10px;
            color: var(--muted);
        }
        .section-header.collapsed::after {
            content: '▶';
        }
        .section-body {
            padding: 12px 14px;
            font-size: 12px;
            line-height: 1.5;
        }
        .section-body.collapsed {
            display: none;
        }
        .task-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .task-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .task-desc {
            flex: 1;
            font-size: 12px;
        }
        .task-badge {
            font-size: 9px;
            text-transform: uppercase;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            background: var(--border);
            color: var(--muted);
        }
        .task-badge.active { background: rgba(0,212,255,0.15); color: var(--accent); }
        .task-badge.committed { background: rgba(34,197,94,0.15); color: var(--success); }
        .task-badge.queued { background: rgba(100,116,139,0.15); color: var(--muted); }
        .progress-track {
            width: 100px;
            height: 6px;
            background: var(--border);
            border-radius: 3px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: var(--accent);
            width: 0%;
            transition: width 0.4s ease;
        }
        .prompt-pre {
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            font-size: 11px;
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 6px;
            white-space: pre-wrap;
            word-break: break-word;
            color: #a5b4fc;
            max-height: 300px;
            overflow-y: auto;
        }
        .thought-stream {
            font-family: 'Fira Code', 'JetBrains Mono', monospace;
            font-size: 11px;
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 6px;
            max-height: 300px;
            overflow-y: auto;
            color: #cbd5e1;
        }
        .thought-line {
            margin-bottom: 4px;
            border-left: 2px solid var(--border);
            padding-left: 8px;
        }
        .thought-line .ts {
            color: var(--muted);
            font-size: 10px;
        }
        .thought-line .type {
            color: var(--accent);
            font-size: 10px;
            text-transform: uppercase;
        }
        .sparkline-canvas {
            width: 100%;
            height: 80px;
            background: rgba(0,0,0,0.2);
            border-radius: 6px;
        }
        .telemetry-legend {
            display: flex;
            gap: 16px;
            margin-top: 8px;
            font-size: 11px;
        }
        .telemetry-legend span {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .telemetry-legend .dot {
            width: 8px;
            height: 8px;
            border-radius: 2px;
        }
        .steer-bar {
            padding: 10px 14px;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 8px;
            background: var(--panel);
        }
        .steer-input {
            flex: 1;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 6px 10px;
            color: var(--text);
            font-size: 12px;
            outline: none;
        }
        .steer-input:focus { border-color: var(--accent); }
        .steer-btn {
            padding: 6px 14px;
            border-radius: 6px;
            border: none;
            background: var(--accent);
            color: #000;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
        }
        .footer-bar {
            padding: 8px 14px;
            font-size: 11px;
            color: var(--muted);
            border-top: 1px solid var(--border);
            background: var(--panel);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .circuit-orb {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }
        .empty-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--muted);
            font-size: 13px;
            gap: 8px;
        }
        .empty-state .big-led {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: var(--muted);
            opacity: 0.3;
        }
        .ws-status {
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 4px;
            background: var(--border);
        }
        .ws-status.connected { background: rgba(34,197,94,0.15); color: var(--success); }
        .ws-status.disconnected { background: rgba(239,68,68,0.15); color: var(--error); }
    </style>
</head>
<body data-session="${sid}">
    <div class="header">
        <h1>🛰️ Command Viewport</h1>
        <span class="session-id" id="sessionId">--</span>
    </div>
    <div class="main">
        <div class="tree-pane">
            <div class="tree-header">
                <span>Agent Circuit</span>
                <span class="ws-status disconnected" id="wsStatus">Offline</span>
            </div>
            <div class="tree-filter">
                <button class="active" id="filterAll">All</button>
                <button id="filterActive">Active</button>
            </div>
            <div class="tree-scroll" id="treeScroll">
                <div class="empty-state" id="treeEmpty">
                    <div class="big-led"></div>
                    <div>No session active</div>
                </div>
            </div>
        </div>
        <div class="viewport-pane" id="viewportPane">
            <div class="empty-state" id="viewportEmpty">
                <div class="big-led"></div>
                <div>Select an agent to inspect</div>
            </div>
        </div>
    </div>
    <div class="footer-bar" id="footerBar">
        <span><span class="circuit-orb" id="circuitOrb"></span><span id="circuitText">Circuit: Standby</span></span>
        <span id="bottleneckText">Bottleneck: None</span>
    </div>

    <script src="${scriptUri}"></script>
</body>
</html>`;
    }
}
