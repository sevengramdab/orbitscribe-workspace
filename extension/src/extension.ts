import * as vscode from 'vscode';
import { SwarmPanel } from './panels/SwarmPanel';
import { BackendService } from './services/BackendService';

let backendService: BackendService;

export function activate(context: vscode.ExtensionContext) {
    backendService = new BackendService();
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
            // Trigger voice input via OrbitScribe if available
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
        }),
        vscode.commands.registerCommand('orbitscribe.openFile', (item: vscode.TreeItem) => {
            // Placeholder for file open
        })
    );

    // Handle webview messages for workspace context
    if (SwarmPanel.currentPanel) {
        // This is handled in the panel's onDidReceiveMessage
    }
}

export function deactivate() {
    backendService?.stop();
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

    getChildren(element?: vscode.TreeItem): Thenable<vscode.TreeItem[]> {
        if (!element) {
            return Promise.resolve([
                createAgentItem('📝 Writer', 'Creative writing & documentation'),
                createAgentItem('🔧 Code', 'Code generation & refactoring'),
                createAgentItem('🧪 Test', 'Test writing & coverage'),
                createAgentItem('🔍 Review', 'Code review & analysis'),
                createAgentItem('📋 Plan', 'Architecture & planning'),
            ]);
        }
        return Promise.resolve([]);
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

    getChildren(element?: vscode.TreeItem): Thenable<vscode.TreeItem[]> {
        if (!element) {
            return Promise.resolve([
                createFileItem('📄 README.md'),
                createFileItem('📄 package.json'),
                createFileItem('📄 src/extension.ts'),
            ]);
        }
        return Promise.resolve([]);
    }
}

function createAgentItem(label: string, description: string): vscode.TreeItem {
    const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
    item.description = description;
    item.command = { command: 'orbitscribe.selectAgent', title: 'Select Agent', arguments: [item] };
    return item;
}

function createFileItem(label: string): vscode.TreeItem {
    const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
    item.command = { command: 'orbitscribe.openFile', title: 'Open File', arguments: [item] };
    return item;
}
