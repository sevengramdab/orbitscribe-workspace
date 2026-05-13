import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

export class CommandDeckPanel {
    public static currentPanel: CommandDeckPanel | undefined;
    public static readonly viewType = 'orbitscribe.commandDeck';
    private readonly _panel: vscode.WebviewPanel;

    public static createOrShow(extensionUri: vscode.Uri) {
        const column = vscode.ViewColumn.Beside;

        if (CommandDeckPanel.currentPanel) {
            CommandDeckPanel.currentPanel._panel.reveal(column);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            CommandDeckPanel.viewType,
            'ORBIT Command Deck',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri],
            }
        );

        CommandDeckPanel.currentPanel = new CommandDeckPanel(panel, extensionUri);
    }

    private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
        this._panel = panel;
        this._panel.webview.html = CommandDeckPanel.getHtml(this._panel.webview, extensionUri);

        this._panel.onDidDispose(() => {
            CommandDeckPanel.currentPanel = undefined;
        });

        this._panel.webview.onDidReceiveMessage(async (message) => {
            switch (message.command) {
                case 'openFile': {
                    try {
                        if (message.path) {
                            const folders = vscode.workspace.workspaceFolders;
                            const workspaceRoot = folders?.[0]?.uri?.fsPath ?? '';
                            let targetPath = message.path;
                            // Resolve relative paths against workspace root
                            if (workspaceRoot && !path.isAbsolute(targetPath)) {
                                targetPath = path.join(workspaceRoot, targetPath);
                            }
                            const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(targetPath));
                            await vscode.window.showTextDocument(doc);
                        }
                    } catch (err: any) {
                        vscode.window.showErrorMessage(`❌ Could not open file: ${err.message || err}`);
                    }
                    break;
                }
                case 'openFolder': {
                    if (message.path) {
                        const uri = vscode.Uri.file(message.path);
                        await vscode.commands.executeCommand('vscode.openFolder', uri, true);
                    }
                    break;
                }
            }
        });
    }

    public static getHtml(webview: vscode.Webview, extensionUri: vscode.Uri): string {
        const dashboardPath = path.join(extensionUri.fsPath, 'orbitscribe-dashboard.html');
        let html: string;
        try {
            html = fs.readFileSync(dashboardPath, 'utf-8');
        } catch (e) {
            return `<!DOCTYPE html><html><body style="padding:20px;color:#ef4444;font-family:sans-serif;">
                <h3>Command Deck not found</h3>
                <p>Could not load ${dashboardPath}</p>
            </body></html>`;
        }

        // Inject CSP if not present
        if (!html.includes('Content-Security-Policy')) {
            const csp = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline' ${webview.cspSource}; script-src 'self' 'unsafe-inline' ${webview.cspSource}; connect-src http://127.0.0.1:* ws://127.0.0.1:*;">`;
            html = html.replace('<meta charset="UTF-8">', `<meta charset="UTF-8">\n    ${csp}`);
        }

        // Inject VS Code: API bridge for opening files
        const bridge = `
<script>
(function() {
    try {
        const vscode = acquireVsCodeApi();
        window.openVSCodeFile = function(filePath) {
            vscode.postMessage({ command: 'openFile', path: filePath });
        };
        window.openVSCodeFolder = function(folderPath) {
            vscode.postMessage({ command: 'openFolder', path: folderPath });
        };
    } catch(e) {
        console.log('VS Code: API not available (running outside webview)');
    }
})();
</script>`;
        html = html.replace('</body>', bridge + '\n</body>');

        return html;
    }
}
