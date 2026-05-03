import * as vscode from 'vscode';

export class SwarmPanel {
    public static currentPanel: SwarmPanel | undefined;
    public static readonly viewType = 'orbitscribe.swarmPanel';
    private readonly _panel: vscode.WebviewPanel;

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
            'OrbitScribe Swarm',
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
        this._panel.webview.html = SwarmPanel.getHtml(this._panel.webview, extensionUri, initialMode);

        this._panel.onDidDispose(() => {
            SwarmPanel.currentPanel = undefined;
        });

        this._panel.webview.onDidReceiveMessage(async (message) => {
            // Forward to extension.ts handler via the panel's webview
            // This is handled by the WebviewViewProvider in extension.ts
        });
    }

    sendMessage(message: any) {
        this._panel.webview.postMessage(message);
    }

    public static getHtml(webview: vscode.Webview, extensionUri: vscode.Uri, initialMode?: string): string {
        const nonce = getNonce();
        const mode = initialMode || 'ask';

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}'; connect-src http://127.0.0.1:*;">
    <title>OrbitScribe Swarm</title>
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
        .message .agent-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--accent);
            margin-bottom: 4px;
            font-weight: 600;
        }
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
        .send-btn, .voice-btn {
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
        }
        .send-btn:hover, .voice-btn:hover { background: var(--accent-hover); }
        .voice-btn {
            background: var(--panel);
            border: 1px solid var(--border);
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
    </style>
</head>
<body>
    <div class="header">
        <h1>🐝 ORBITSCRIBE SWARM</h1>
    </div>
    <div class="mode-tabs">
        <button class="mode-tab ${mode === 'ask' ? 'active' : ''}" data-mode="ask">Ask</button>
        <button class="mode-tab ${mode === 'plan' ? 'active' : ''}" data-mode="plan">Plan</button>
        <button class="mode-tab ${mode === 'agent' ? 'active' : ''}" data-mode="agent">Agent</button>
        <button class="mode-tab ${mode === 'swarm' ? 'active' : ''}" data-mode="swarm">Swarm</button>
    </div>
    <div class="chat-area" id="chatArea"></div>
    <div class="input-area">
        <textarea class="chat-input" id="chatInput" rows="2" placeholder="Ask, plan, or delegate..."></textarea>
        <button class="voice-btn" id="voiceBtn" title="Voice input (requires OrbitScribe)">🎤</button>
        <button class="send-btn" id="sendBtn">➤</button>
    </div>
    <div class="status-bar">
        <span id="statusText">Ready</span>
        <span class="api-badge local" id="apiBadge">Auto</span>
    </div>

    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const chatArea = document.getElementById('chatArea');
        const chatInput = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');
        const voiceBtn = document.getElementById('voiceBtn');
        const statusText = document.getElementById('statusText');
        const apiBadge = document.getElementById('apiBadge');

        let currentMode = '${mode}';
        let isStreaming = false;
        let eventSource = null;

        // Mode switching
        document.querySelectorAll('.mode-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentMode = tab.dataset.mode;
                addMessage('system', `Switched to **${currentMode.toUpperCase()}** mode`);
            });
        });

        function addMessage(role, text, agentName) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            if (agentName) {
                div.innerHTML = '<div class="agent-label">' + agentName + '</div>' + escapeHtml(text);
            } else {
                div.innerHTML = escapeHtml(text);
            }
            chatArea.appendChild(div);
            chatArea.scrollTop = chatArea.scrollHeight;
            return div;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML.replace(/\n/g, '<br>');
        }

        async function sendMessage() {
            const text = chatInput.value.trim();
            if (!text || isStreaming) return;

            chatInput.value = '';
            addMessage('user', text);
            isStreaming = true;
            statusText.textContent = currentMode === 'swarm' ? 'Swarm running...' : 'Thinking...';
            statusText.classList.add('loading');

            // Get workspace context first
            vscode.postMessage({ command: 'getWorkspaceContext' });

            // Wait a moment for workspace context, then send
            setTimeout(async () => {
                await streamChat(text);
            }, 300);
        }

        async function streamChat(text) {
            try {
                const resp = await fetch('http://127.0.0.1:58081/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: text,
                        mode: currentMode,
                        workspace_context: window.workspaceContext || '',
                    }),
                });

                const reader = resp.body.getReader();
                const decoder = new TextDecoder();
                let assistantMsg = null;
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.chunk) {
                                    if (!assistantMsg) {
                                        assistantMsg = addMessage('assistant', '');
                                    }
                                    assistantMsg.innerHTML += escapeHtml(data.chunk);
                                    chatArea.scrollTop = chatArea.scrollHeight;
                                }
                                if (data.done) {
                                    isStreaming = false;
                                    statusText.textContent = 'Ready';
                                    statusText.classList.remove('loading');
                                }
                            } catch (e) {}
                        }
                    }
                }
            } catch (e) {
                addMessage('assistant', 'Error: ' + e.message);
                isStreaming = false;
                statusText.textContent = 'Error';
                statusText.classList.remove('loading');
            }
        }

        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        voiceBtn.addEventListener('click', () => {
            vscode.postMessage({ command: 'triggerVoice' });
        });

        // Handle messages from extension
        window.addEventListener('message', (e) => {
            const msg = e.data;
            switch (msg.command) {
                case 'workspaceContext':
                    window.workspaceContext = msg.context;
                    break;
                case 'setMode':
                    currentMode = msg.mode;
                    document.querySelectorAll('.mode-tab').forEach(t => {
                        t.classList.toggle('active', t.dataset.mode === currentMode);
                    });
                    break;
                case 'triggerVoice':
                    addMessage('system', '🎤 Voice input ready — speak into OrbitScribe');
                    break;
            }
        });
    </script>
</body>
</html>`;
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
