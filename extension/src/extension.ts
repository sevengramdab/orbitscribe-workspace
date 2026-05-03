import * as vscode from 'vscode';
import * as path from 'path';
import { SwarmPanel } from './panels/SwarmPanel';
import { BackendService } from './services/BackendService';

let backendService: BackendService;

export async function activate(context: vscode.ExtensionContext) {
    backendService = new BackendService();

    // Check Ollama status
    const hasOllama = await backendService.checkOllama();
    if (!hasOllama) {
        const action = await vscode.window.showWarningMessage(
            '⚠️ Ollama is not running. Local LLMs will be unavailable.',
            'Start Ollama', 'Use Cloud Only', 'Ignore'
        );
        if (action === 'Start Ollama') {
            try {
                const { spawn } = require('child_process');
                spawn('ollama', ['serve'], { detached: true, stdio: 'ignore' });
                vscode.window.showInformationMessage('Starting Ollama...');
            } catch {
                vscode.window.showErrorMessage('Failed to start Ollama. Is it installed?');
            }
        } else if (action === 'Use Cloud Only') {
            await vscode.workspace.getConfiguration('orbitscribe').update('apiMode', 'cloud_only', true);
            vscode.window.showInformationMessage('Switched to cloud-only mode.');
        }
    }

    // Start swarm backend
    backendService.ensureRunning().catch(err => {
        console.error('Failed to start swarm backend:', err);
    });

    // Tree data providers for sidebar views
    const agentsProvider = new AgentsTreeProvider();
    const filesProvider = new FilesTreeProvider();

    vscode.window.registerTreeDataProvider('swarmAgents', agentsProvider);
    vscode.window.registerTreeDataProvider('swarmFiles', filesProvider);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('orbitscribe.openSwarmPanel', () => {
            SwarmPanel.createOrShow(context.extensionUri, 'ask');
        }),
        vscode.commands.registerCommand('orbitscribe.openSwarmPanelAsk', () => {
            SwarmPanel.createOrShow(context.extensionUri, 'ask');
        }),
        vscode.commands.registerCommand('orbitscribe.openSwarmPanelPlan', () => {
            SwarmPanel.createOrShow(context.extensionUri, 'plan');
        }),
        vscode.commands.registerCommand('orbitscribe.openSwarmPanelAgent', () => {
            SwarmPanel.createOrShow(context.extensionUri, 'agent');
        }),
        vscode.commands.registerCommand('orbitscribe.openSwarmPanelSwarm', () => {
            SwarmPanel.createOrShow(context.extensionUri, 'swarm');
        }),
        vscode.commands.registerCommand('orbitscribe.voiceInput', () => {
            SwarmPanel.createOrShow(context.extensionUri, 'ask');
            setTimeout(() => {
                SwarmPanel.currentPanel?.sendMessage({ command: 'triggerVoice' });
            }, 300);
        }),
        vscode.commands.registerCommand('orbitscribe.refreshAgents', () => {
            agentsProvider.refresh();
        }),
        vscode.commands.registerCommand('orbitscribe.refreshFiles', () => {
            filesProvider.refresh();
        }),
        vscode.commands.registerCommand('orbitscribe.selectAgent', (item: vscode.TreeItem) => {
            SwarmPanel.createOrShow(context.extensionUri, 'agent');
            const agentName = item.label?.toString().replace(/^[^\w]+/, '').toLowerCase();
            setTimeout(() => {
                SwarmPanel.currentPanel?.sendMessage({ command: 'setAgent', agent: agentName });
            }, 300);
        }),
        vscode.commands.registerCommand('orbitscribe.openFile', async (item: vscode.TreeItem) => {
            const label = item.label?.toString().replace(/^[^\w]+/, '') || '';
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (workspaceFolders && label) {
                const filePath = path.join(workspaceFolders[0].uri.fsPath, label);
                const doc = await vscode.workspace.openTextDocument(filePath);
                await vscode.window.showTextDocument(doc);
            }
        })
    );
}

export function deactivate() {
    backendService?.stop();
}

// --- Workspace Context Helper ---

export async function getWorkspaceContext(): Promise<string> {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders) {
        return 'No workspace open.';
    }

    let context = '';
    for (const folder of folders) {
        context += `Workspace: ${folder.name}\n`;
        try {
            const files = await vscode.workspace.findFiles(
                new vscode.RelativePattern(folder, '**/*.{ts,js,py,md,json,html,css}'),
                '**/node_modules/**',
                50
            );
            context += 'Files:\n';
            for (const file of files.slice(0, 30)) {
                const rel = path.relative(folder.uri.fsPath, file.fsPath);
                context += `  - ${rel}\n`;
            }
        } catch {
            context += '  (unable to list files)\n';
        }
    }

    // Add open editor context
    const active = vscode.window.activeTextEditor;
    if (active) {
        const doc = active.document;
        const selection = active.selection;
        context += `\nActive file: ${path.basename(doc.fileName)}\n`;
        if (!selection.isEmpty) {
            context += `Selected code:\n${doc.getText(selection)}\n`;
        }
    }

    return context;
}

// --- Tree Providers ---

class AgentsTreeProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<vscode.TreeItem | undefined | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: vscode.TreeItem): Promise<vscode.TreeItem[]> {
        if (!element) {
            // Fetch from backend
            try {
                const resp = await fetch('http://127.0.0.1:58081/api/agents');
                if (resp.ok) {
                    const data = await resp.json() as Record<string, {name: string; role: string}>;
                    return Object.entries(data).map(([key, info]) =>
                        createAgentItem(info.name, info.role, key)
                    );
                }
            } catch {
                // fallback to static list
            }
            return [
                createAgentItem('📝 Writer', 'Creative writing & documentation', 'doc'),
                createAgentItem('🔧 Code', 'Code generation & refactoring', 'code'),
                createAgentItem('🧪 Test', 'Test writing & coverage', 'test'),
                createAgentItem('🔍 Review', 'Code review & analysis', 'review'),
                createAgentItem('📋 Plan', 'Architecture & planning', 'plan'),
            ];
        }
        return [];
    }
}

class FilesTreeProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
    private _onDidChangeTreeData = new vscode.EventEmitter<vscode.TreeItem | undefined | void>();
    readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: vscode.TreeItem): Promise<vscode.TreeItem[]> {
        if (!element) {
            const folders = vscode.workspace.workspaceFolders;
            if (!folders) {
                return [new vscode.TreeItem('No workspace open', vscode.TreeItemCollapsibleState.None)];
            }
            const items: vscode.TreeItem[] = [];
            for (const folder of folders) {
                try {
                    const files = await vscode.workspace.findFiles(
                        new vscode.RelativePattern(folder, '**/*.{ts,js,py,md,json,html,css}'),
                        '**/node_modules/**',
                        20
                    );
                    for (const file of files.slice(0, 15)) {
                        const rel = path.relative(folder.uri.fsPath, file.fsPath);
                        items.push(createFileItem(rel, file.fsPath));
                    }
                } catch {
                    items.push(new vscode.TreeItem('(unable to read)', vscode.TreeItemCollapsibleState.None));
                }
            }
            return items;
        }
        return [];
    }
}

function createAgentItem(label: string, description: string, key: string): vscode.TreeItem {
    const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
    item.description = description;
    item.command = { command: 'orbitscribe.selectAgent', title: 'Select Agent', arguments: [item] };
    return item;
}

function createFileItem(label: string, fullPath: string): vscode.TreeItem {
    const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
    item.tooltip = fullPath;
    item.command = { command: 'orbitscribe.openFile', title: 'Open File', arguments: [item] };
    return item;
}
