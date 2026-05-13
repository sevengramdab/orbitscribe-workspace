import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';
import { SwarmPanel } from './panels/SwarmPanel';
import { CommandViewport } from './panels/CommandViewport';
import { CommandDeckPanel } from './panels/CommandDeckPanel';
import { JukeboxPanel } from './panels/JukeboxPanel';
import { OrbitScribeSidebarProvider } from './panels/OrbitScribeSidebarProvider';
import { BackendService } from './services/BackendService';
import { VoiceBackendService } from './services/VoiceBackendService';

let backendService: BackendService;
let voiceBackendService: VoiceBackendService;
let sidebarProvider: OrbitScribeSidebarProvider;

export async function activate(context: vscode.ExtensionContext) {
    try {
        console.log('[OrbitScribe] activate() started');

            // ── Crash-Resilient Auto-Resume ───────────────────────────────────
        const now = Date.now();
        // Robust workspace root resolution
        let workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '';
        // Fallback 1: try to find tools dir near extension install
        if (!workspaceRoot || !fs.existsSync(path.join(workspaceRoot, 'tools'))) {
            const extParent = path.join(context.extensionPath, '..');
            if (fs.existsSync(path.join(extParent, 'tools'))) {
                workspaceRoot = extParent;
            }
        }
        // Fallback 2: try hardcoded project root
        if (!workspaceRoot || !fs.existsSync(path.join(workspaceRoot, 'tools'))) {
            const hardcoded = 'C:\\Users\\Shadow\\voice to text engine';
            if (fs.existsSync(path.join(hardcoded, 'tools'))) {
                workspaceRoot = hardcoded;
            }
        }
        // Fallback 3: use extension path parent as last resort
        if (!workspaceRoot) {
            workspaceRoot = path.join(context.extensionPath, '..');
        }
        const toolsDir = path.join(workspaceRoot, 'tools');
        const lockFile = path.join(toolsDir, '.reload-resume-lock');
        const heartbeatFile = path.join(toolsDir, '.orbitscribe-heartbeat');
        const sessionFile = path.join(toolsDir, '.kimi-last-session');
        const resumeDebugLog = path.join(toolsDir, '.orbitscribe-resume-debug.log');

        function debugLog(msg: string) {
            try {
                fs.appendFileSync(resumeDebugLog, `${new Date().toISOString()} [${process.pid}] ${msg}\n`);
            } catch { /* ignore */ }
            console.log(msg);
        }

        // Helper: write heartbeat file for crash detection (external processes can read this)
        function writeHeartbeat(sessionId?: string) {
            try {
                const hb = {
                    timestamp: Date.now(),
                    pid: process.pid,
                    sessionId: sessionId || '',
                };
                fs.writeFileSync(heartbeatFile, JSON.stringify(hb));
            } catch (e) {
                console.error('[OrbitScribe] Failed to write heartbeat:', e);
            }
        }

        // Helper: clean stale lock files (crash leaves these behind because deactivate() never runs)
        function cleanStaleLock() {
            try {
                if (!fs.existsSync(lockFile)) { return; }
                const raw = fs.readFileSync(lockFile, 'utf-8').trim();
                let stale = false;
                // Try JSON format {timestamp, pid}
                try {
                    const lock = JSON.parse(raw);
                    const lockAge = now - (lock.timestamp || 0);
                    if (lockAge > 300_000) { // >5 min old
                        stale = true;
                    } else if (lock.pid) {
                        try {
                            const { execSync } = require('child_process');
                            execSync(`tasklist /FI "PID eq ${lock.pid}" 2>nul`, { timeout: 3000, stdio: 'pipe' });
                            // PID exists — lock is still valid only if recent
                            stale = lockAge > 300_000;
                        } catch {
                            stale = true; // PID not found → process is dead
                        }
                    }
                } catch {
                    // Legacy format: just a timestamp string
                    const lockTime = parseInt(raw, 10);
                    stale = isNaN(lockTime) || (now - lockTime) > 300_000;
                }
                if (stale) {
                    fs.unlinkSync(lockFile);
                    console.log('[OrbitScribe] Stale lock file removed (crash recovery).');
                }
            } catch (e) {
                console.error('[OrbitScribe] Error cleaning lock file:', e);
            }
        }

        // Helper: read session ID from multiple sources
        function resolveSessionId(): string {
            let sid = '';
            try {
                if (fs.existsSync(sessionFile)) {
                    sid = fs.readFileSync(sessionFile, 'utf-8').trim();
                }
            } catch (e) { /* ignore */ }
            if (!sid) {
                try {
                    const resumeCmdFile = path.join(toolsDir, '.kimi-resume-cmd.txt');
                    if (fs.existsSync(resumeCmdFile)) {
                        const cmd = fs.readFileSync(resumeCmdFile, 'utf-8').trim();
                        const match = cmd.match(/kimi\s+-r\s+(\S+)/);
                        if (match) { sid = match[1]; }
                    }
                } catch (e) { /* ignore */ }
            }
            if (!sid) {
                try {
                    const sessionsDir = path.join(os.homedir(), '.kimi', 'sessions');
                    if (fs.existsSync(sessionsDir)) {
                        const dirs = fs.readdirSync(sessionsDir)
                            .filter(d => fs.statSync(path.join(sessionsDir, d)).isDirectory())
                            .sort((a, b) => fs.statSync(path.join(sessionsDir, b)).mtimeMs - fs.statSync(path.join(sessionsDir, a)).mtimeMs);
                        if (dirs.length > 0) { sid = dirs[0]; }
                    }
                } catch (e) { /* ignore */ }
            }
            return sid;
        }

        // Helper: trigger terminal-based auto-resume
        function triggerAutoResume(resumeContext: string, sessionId: string, reason: string) {
            const workDir = workspaceRoot;
            debugLog(`[RESUME] ${reason}. Scheduling terminal auto-resume. session=${sessionId}, workDir=${workDir}`);
            try {
                fs.writeFileSync(lockFile, JSON.stringify({ timestamp: Date.now(), pid: process.pid }));
                debugLog('[RESUME] Lock file created.');
            } catch (e: any) {
                debugLog(`[RESUME] Failed to create auto-resume lock: ${e.message || e}`);
            }

            setTimeout(async () => {
                debugLog('[RESUME] Timer fired (15s). Creating terminal...');
                let terminal: vscode.Terminal | undefined;
                let isNewTerminal = false;
                try {
                    terminal = vscode.window.terminals.find(t => t.name === 'Kimi Auto-Resume');
                    debugLog(`[RESUME] Existing 'Kimi Auto-Resume' terminal found: ${!!terminal}`);
                    if (!terminal) {
                        debugLog(`[RESUME] Creating new terminal with cwd=${workDir}`);
                        terminal = vscode.window.createTerminal({ name: 'Kimi Auto-Resume', cwd: workDir });
                        isNewTerminal = true;
                        debugLog('[RESUME] Terminal created successfully.');
                    }
                } catch (e: any) {
                    debugLog(`[RESUME] ERROR creating/finding terminal: ${e.message || e}`);
                    vscode.window.showWarningMessage('⚠️ Auto-resume: failed to create terminal.');
                    return;
                }

                try {
                    terminal.show();

                    // New terminals need time for the shell (PowerShell) to fully initialize
                    // before accepting input. Sending text too early causes buffer corruption.
                    const initDelay = isNewTerminal ? 2500 : 100;
                    debugLog(`[RESUME] Waiting ${initDelay}ms for terminal to be ready (new=${isNewTerminal})...`);

                    setTimeout(() => {
                        try {
                            // Ensure clean shell prompt — interrupt any running process
                            terminal.sendText('\x03', false);
                            debugLog('[RESUME] Sent Ctrl+C to terminal.');

                            // Flush any pending state with a blank line before the history command
                            setTimeout(() => {
                                try {
                                    terminal.sendText('', true);
                                } catch { /* ignore */ }
                            }, 400);

                            // Show recent chat history before resuming so the user sees context
                            setTimeout(() => {
                                try {
                                    const historyCmd = `python tools/show_kimi_history.py ${sessionId} --turns 5`;
                                    debugLog(`[RESUME] Sending history command: ${historyCmd}`);
                                    terminal.sendText(historyCmd, true);
                                } catch (e: any) {
                                    debugLog(`[RESUME] ERROR sending history command: ${e.message || e}`);
                                }
                            }, 1000);

                            // Wait for history to print before launching kimi TUI
                            setTimeout(() => {
                                try {
                                    // Escape backslashes for PowerShell path
                                    const safeWorkDir = workDir.replace(/\\/g, '\\\\');
                                    const cmd = `kimi -r ${sessionId} -w "${safeWorkDir}"`;
                                    debugLog(`[RESUME] Sending command: ${cmd}`);
                                    terminal.sendText(cmd, true);
                                    debugLog('[RESUME] Resume command sent.');
                                    try { fs.writeFileSync(sessionFile, sessionId); } catch (e) { /* ignore */ }
                                } catch (e: any) {
                                    debugLog(`[RESUME] ERROR sending resume command: ${e.message || e}`);
                                }
                            }, 4500);

                            // Send context after TUI loads
                            setTimeout(() => {
                                try {
                                    terminal.sendText(resumeContext, true);
                                    debugLog('[RESUME] Context sent to terminal.');
                                    vscode.window.showInformationMessage('🤖 Kimi session auto-resumed in terminal.');
                                } catch (e: any) {
                                    debugLog(`[RESUME] ERROR sending context: ${e.message || e}`);
                                }
                            }, 14000);
                        } catch (e: any) {
                            debugLog(`[RESUME] ERROR in terminal.sendText: ${e.message || e}`);
                            vscode.window.showWarningMessage('⚠️ Auto-resume failed. Run `kimi -r <session>` manually in terminal.');
                        }
                    }, initDelay);
                } catch (e: any) {
                    debugLog(`[RESUME] ERROR in terminal.sendText: ${e.message || e}`);
                    vscode.window.showWarningMessage('⚠️ Auto-resume failed. Run `kimi -r <session>` manually in terminal.');
                }
            }, 15000);

            setTimeout(() => {
                try { if (fs.existsSync(lockFile)) { fs.unlinkSync(lockFile); } } catch { /* ignore */ }
                debugLog('[RESUME] Lock file cleaned up.');
            }, 45000);
        }

        // 1. Always clean stale locks on activate (crash leaves them behind)
        cleanStaleLock();

        // 2. Detect reload vs crash
        const lastActive = context.globalState.get<number>('orbitscribe.lastActive', 0);
        const isReload = lastActive > 0 && (now - lastActive) < 120_000; // clean reload <2 min
        let isCrashRecovery = false;
        let recoveredSessionId = '';
        try {
            if (fs.existsSync(heartbeatFile)) {
                const hb = JSON.parse(fs.readFileSync(heartbeatFile, 'utf-8'));
                const hbAge = now - (hb.timestamp || 0);
                // Skip shutdown heartbeats (clean exit) unless very old (>30 min)
                const wasCleanShutdown = hb.status === 'shutdown';
                if (wasCleanShutdown && hbAge < 1_800_000) {
                    debugLog(`[RESUME] Heartbeat shows clean shutdown, age=${Math.round(hbAge/1000)}s. Skipping crash recovery.`);
                } else if (hbAge > 120_000 && hbAge < 1_800_000) { // 2 min … 30 min
                    isCrashRecovery = true;
                    recoveredSessionId = hb.sessionId || '';
                    debugLog(`[RESUME] Crash detected via stale heartbeat. age=${Math.round(hbAge/1000)}s, session=${recoveredSessionId}`);
                }
            }
        } catch (e) { /* ignore malformed heartbeat */ }

        // 3. Trigger recovery if needed
        if (isReload || isCrashRecovery) {
            const contextFile = path.join(toolsDir, '.reload-context.txt');
            let resumeContext = 'Continue from where we left off.';
            try {
                if (fs.existsSync(contextFile)) {
                    resumeContext = fs.readFileSync(contextFile, 'utf-8').trim();
                    fs.unlinkSync(contextFile);
                }
            } catch (e) {
                console.error('[OrbitScribe] Failed to read context file:', e);
            }

            const sessionId = recoveredSessionId || resolveSessionId();
            debugLog(`[RESUME] sessionId=${sessionId}, isReload=${isReload}, isCrashRecovery=${isCrashRecovery}`);
            if (sessionId) {
                const reason = isReload ? 'Reload detected' : 'Crash recovery';
                if (!fs.existsSync(lockFile)) {
                    debugLog('[RESUME] No lock file. Triggering auto-resume...');
                    triggerAutoResume(resumeContext, sessionId, reason);
                } else {
                    debugLog('[RESUME] Lock file exists. Skipping duplicate auto-resume.');
                }
            } else {
                debugLog('[RESUME] No session ID found. Auto-resume skipped.');
                vscode.window.showWarningMessage('⚠️ No Kimi session ID found. Auto-resume skipped.');
            }
        }

        // 4. Keep-alive: update globalState AND write heartbeat file
        context.globalState.update('orbitscribe.lastActive', now);
        writeHeartbeat(resolveSessionId());
        const keepAlive = setInterval(() => {
            const ts = Date.now();
            context.globalState.update('orbitscribe.lastActive', ts);
            writeHeartbeat(resolveSessionId());
        }, 30_000);
        context.subscriptions.push({ dispose: () => clearInterval(keepAlive) });

        // 5. Start external watchdog (safety net for when VS Code: doesn't auto-restart extension host)
        try {
            const watchdogPath = path.join(toolsDir, 'resume_watchdog.py');
            if (fs.existsSync(watchdogPath)) {
                const { spawn } = require('child_process');
                const watchdogPidFile = path.join(toolsDir, '.watchdog.pid');
                let alreadyRunning = false;
                try {
                    if (fs.existsSync(watchdogPidFile)) {
                        const wpid = parseInt(fs.readFileSync(watchdogPidFile, 'utf-8').trim(), 10);
                        if (!isNaN(wpid)) {
                            const { execSync } = require('child_process');
                            try {
                                execSync(`tasklist /FI "PID eq ${wpid}" 2>nul`, { timeout: 3000, stdio: 'pipe' });
                                alreadyRunning = true;
                            } catch { /* not running */ }
                        }
                    }
                } catch { /* ignore */ }
                if (!alreadyRunning) {
                    const child = spawn('python', [watchdogPath], { detached: true, stdio: 'ignore' });
                    child.unref();
                    console.log('[OrbitScribe] Started resume watchdog (PID:', child.pid, ')');
                } else {
                    console.log('[OrbitScribe] Resume watchdog already running.');
                }
            }
        } catch (e) {
            console.error('[OrbitScribe] Failed to start watchdog:', e);
        }
        // ──────────────────────────────────────────────────────────────────

        backendService = new BackendService();
        voiceBackendService?.dispose();
        voiceBackendService = new VoiceBackendService();
        context.subscriptions.push({ dispose: () => voiceBackendService?.dispose() });

        // Start voice backend (non-blocking)
        voiceBackendService.ensureRunning().catch(err => {
            console.error('Failed to start voice backend:', err);
        });

        // Ensure Ollama is ready before starting backend
        const ollamaReadyPromise = backendService.checkOllama().then(async (hasOllama) => {
            if (!hasOllama) {
                try {
                    const { spawn } = require('child_process');
                    spawn('ollama', ['serve'], { detached: true, stdio: 'ignore' });
                    vscode.window.showInformationMessage('🦙 Starting Ollama server...');
                } catch {
                    vscode.window.showWarningMessage('⚠️ Ollama is not installed. Local LLMs will be unavailable.');
                    return;
                }
                // Poll until Ollama is responsive (up to 15s)
                for (let i = 0; i < 30; i++) {
                    await new Promise(r => setTimeout(r, 500));
                    if (await backendService.checkOllama()) {
                        vscode.window.showInformationMessage('🦙 Ollama is online.');
                        return;
                    }
                }
                vscode.window.showWarningMessage('⚠️ Ollama failed to start within 15 seconds.');
            }
        }).catch(() => { /* silently ignore */ });

        // Start backend after Ollama attempt (don't block on it)
        ollamaReadyPromise.then(() => {
            backendService.ensureRunning().catch(err => {
                console.error('Failed to start backend:', err);
                vscode.window.showWarningMessage('⚠️ Backend failed to start. Some features may be unavailable.');
            });
        });

        // Tree data providers for sidebar views
        const agentsProvider = new AgentsTreeProvider();
        const filesProvider = new FilesTreeProvider();

        vscode.window.registerTreeDataProvider('swarmAgents', agentsProvider);
        vscode.window.registerTreeDataProvider('swarmFiles', filesProvider);

        // Register sidebar webview provider
        sidebarProvider = new OrbitScribeSidebarProvider(context.extensionUri);
        context.subscriptions.push(
            vscode.window.registerWebviewViewProvider(OrbitScribeSidebarProvider.viewType, sidebarProvider)
        );

        // Forward backend status changes to sidebar
        backendService.onStatusChange((status) => {
            sidebarProvider.sendMessage({
                command: 'backendStatus',
                online: status.online,
                ollama: status.ollama,
                model: status.model,
            });
        });

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
                SwarmPanel.createOrShow(context.extensionUri, 'ask');
            }),
            vscode.commands.registerCommand('orbitscribe.openCommandViewport', () => {
                CommandViewport.createOrShow(context.extensionUri);
            }),
            vscode.commands.registerCommand('orbitscribe.openCommandDeck', () => {
                CommandDeckPanel.createOrShow(context.extensionUri);
            }),
            vscode.commands.registerCommand('orbitscribe.openJukebox', () => {
                JukeboxPanel.createOrShow(context.extensionUri);
            }),
            vscode.commands.registerCommand('orbitscribe.activateMassSwarm', async () => {
                SwarmPanel.createOrShow(context.extensionUri, 'ask');
                SwarmPanel.currentPanel?.reveal();
                // Small delay so SwarmPanel gets focus first, then viewport opens beside
                setTimeout(() => {
                    CommandViewport.createOrShow(context.extensionUri);
                }, 200);
            }),
            vscode.commands.registerCommand('orbitscribe.voiceInput', () => {
                SwarmPanel.createOrShow(context.extensionUri, 'ask');
                setTimeout(() => {
                    SwarmPanel.currentPanel?.sendMessage({ command: 'triggerVoice' });
                }, 300);
            }),
            vscode.commands.registerCommand('orbitscribe.reviewChanges', async () => {
                if (!SwarmPanel.currentPanel) {
                    vscode.window.showWarningMessage('Open the OrbitScribe panel first.');
                    return;
                }
                SwarmPanel.currentPanel.sendMessage({ command: 'requestBatchReview' });
            }),
            vscode.commands.registerCommand('orbitscribe.undoLastBatch', async () => {
                // This would need the latest batch_id; for now instruct the user to use the panel
                vscode.window.showInformationMessage('Use the batch review card in the chat panel to undo changes.');
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
            vscode.commands.registerCommand('orbitscribe.openFile', async (item: vscode.TreeItem) => {
                if (item.tooltip && typeof item.tooltip === 'string') {
                    const doc = await vscode.workspace.openTextDocument(item.tooltip);
                    await vscode.window.showTextDocument(doc);
                }
            }),
            vscode.commands.registerCommand('orbitscribe.compactContext', async () => {
                // Compact both Kimi and OrbitScribe contexts
                const panel = SwarmPanel.currentPanel;
                if (panel) {
                    panel.sendMessage({ command: 'compact' });
                }
                // Also compact backend session if we have one
                try {
                    const { httpPost } = await import('./services/httpUtil');
                    const resp = await httpPost(`${backendService.getBaseUrl()}/api/compact`, { session_id: 'default', summary: '' });
                    const data = await resp.json();
                    if (data.ok) {
                        vscode.window.showInformationMessage(`🗜️ OrbitScribe context compacted (${data.old_message_count} → ${data.new_message_count} messages)`);
                    }
                } catch {
                    // Backend not running, that's ok
                }
            }),
            vscode.commands.registerCommand('orbitscribe.diagnoseVoiceBackend', async () => {
                const lines = await voiceBackendService.diagnose();
                const panel = vscode.window.createWebviewPanel(
                    'orbitscribe.diagnose',
                    'OrbitScribe Voice Diagnostics',
                    vscode.ViewColumn.One,
                    { enableScripts: true }
                );
                panel.webview.html = `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Diagnostics</title></head>
<body style="font-family:monospace;padding:20px;background:#0f1117;color:#e2e8f0;">
<pre>${lines.map(l => l.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')).join('\n')}</pre>
</body>
</html>`;
            }),
            vscode.commands.registerCommand('orbitscribe.restartVoiceBackend', async () => {
                vscode.window.showInformationMessage('🎙️ Restarting Voice Backend...');
                voiceBackendService.stop();
                try {
                    await voiceBackendService.ensureRunning();
                    vscode.window.showInformationMessage('✅ Voice Backend restarted.');
                } catch (err: any) {
                    vscode.window.showErrorMessage(`❌ Restart failed: ${err.message || err}`);
                }
            }),
            vscode.commands.registerCommand('orbitscribe.diagnoseSwarmBackend', async () => {
                const lines: string[] = [];
                lines.push('=== OrbitScribe Backend Diagnostics ===');
                lines.push(`Extension path: ${context.extensionUri.fsPath}`);
                lines.push(`Backend port: ${backendService.getBaseUrl()}`);
                lines.push('');

                const { spawn, execSync } = require('child_process');
                lines.push('--- Python ---');
                for (const py of ['pythonw', 'python', 'py', 'python3']) {
                    try {
                        const ver = execSync(`${py} --version`, { encoding: 'utf-8', timeout: 3000 }).trim();
                        lines.push(`  ✅ ${py}: ${ver}`);
                    } catch {
                        lines.push(`  ❌ ${py}: not found`);
                    }
                }
                lines.push('');

                lines.push('--- Backend Health ---');
                try {
                    const healthy = await backendService.isHealthy();
                    lines.push(`  ${healthy ? '✅' : '❌'} ${backendService.getBaseUrl()}/api/health`);
                } catch (e: any) {
                    lines.push(`  ❌ ${backendService.getBaseUrl()}/api/health — ${e.message || e}`);
                }
                lines.push('');
                lines.push('=== End Diagnostics ===');

                const panel = vscode.window.createWebviewPanel(
                    'orbitscribe.diagnoseSwarm',
                    'OrbitScribe Backend Diagnostics',
                    vscode.ViewColumn.One,
                    { enableScripts: true }
                );
                panel.webview.html = `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Backend Diagnostics</title></head>
<body style="font-family:monospace;padding:20px;background:#0f1117;color:#e2e8f0;">
<pre>${lines.map(l => l.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')).join('\n')}</pre>
</body>
</html>`;
            })
        );

        console.log('[OrbitScribe] activate() completed successfully');
        vscode.window.showInformationMessage('🚀 OrbitScribe is ready. Click the speech-bubble icon in the left sidebar to open.');
    } catch (activateErr: any) {
        const msg = `[OrbitScribe] FATAL ACTIVATION ERROR: ${activateErr.message || activateErr}\n${activateErr.stack || ''}`;
        console.error(msg);
        vscode.window.showErrorMessage(`OrbitScribe failed to activate: ${activateErr.message || activateErr}`);
    }
}

export async function executeTool(tool: string, args: any): Promise<{ status: string; data?: any; error?: string }> {
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
        default:
            throw new Error(`Unknown tool: ${tool}`);
    }
}

export function deactivate() {
    backendService?.stop();
    voiceBackendService?.dispose();

    // Clean up auto-resume lock file so next reload isn't blocked
    try {
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '';
        if (workspaceRoot) {
            const lockFile = path.join(workspaceRoot, 'tools', '.reload-resume-lock');
            if (fs.existsSync(lockFile)) {
                fs.unlinkSync(lockFile);
            }
            // Write shutdown heartbeat so watchdog doesn't think we crashed
            const heartbeatFile = path.join(workspaceRoot, 'tools', '.orbitscribe-heartbeat');
            try {
                const hb = { timestamp: Date.now(), pid: process.pid, sessionId: '', status: 'shutdown' };
                fs.writeFileSync(heartbeatFile, JSON.stringify(hb));
            } catch { /* ignore */ }
        }
    } catch {
        // ignore cleanup errors
    }
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
        if (element) { return []; }
        try {
            const { httpGet } = await import('./services/httpUtil');
            const resp = await httpGet('http://127.0.0.1:58081/api/agents');
            const data = await resp.json();
            const agents = Object.entries(data).map(([key, info]: [string, any]) =>
                createAgentItem(`${info.name || key}`, info.role || '')
            );
            if (agents.length === 0) {
                return [createAgentItem('No agents', 'Backend returned empty list')];
            }
            return agents;
        } catch {
            // Fallback static list if backend is unreachable
            return [
                createAgentItem('📝 Writer', 'Creative writing & documentation'),
                createAgentItem('🔧 Code', 'Code generation & refactoring'),
                createAgentItem('🧪 Test', 'Test writing & coverage'),
                createAgentItem('🔍 Review', 'Code review & analysis'),
                createAgentItem('📋 Plan', 'Architecture & planning'),
            ];
        }
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
        if (element) { return []; }
        const folders = vscode.workspace.workspaceFolders;
        if (!folders) {
            return [createFileItem('No workspace open')];
        }
        try {
            const files = await vscode.workspace.findFiles(
                '**/*.{ts,js,py,md,json,html,css}',
                '**/node_modules/**',
                20
            );
            if (files.length === 0) {
                return [createFileItem('No files found')];
            }
            return files.slice(0, 20).map((f) => {
                const name = path.basename(f.fsPath);
                return createFileItem(`📄 ${name}`, f.fsPath);
            });
        } catch {
            return [createFileItem('Unable to list files')];
        }
    }
}

function createAgentItem(label: string, description: string): vscode.TreeItem {
    const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
    item.description = description;
    item.command = { command: 'orbitscribe.selectAgent', title: 'Select Agent', arguments: [item] };
    return item;
}

function createFileItem(label: string, fsPath?: string): vscode.TreeItem {
    const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
    if (fsPath) {
        item.command = { command: 'orbitscribe.openFile', title: 'Open File', arguments: [item] };
        item.tooltip = fsPath;
    }
    return item;
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
