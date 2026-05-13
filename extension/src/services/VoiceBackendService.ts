import * as vscode from 'vscode';
import { spawn, ChildProcess, execSync } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as http from 'http';
import { httpGet } from './httpUtil';

interface PythonCandidate {
    command: string;
    argsPrefix: string[];
    resolvedPath: string | null;
}

interface ScriptCandidate {
    path: string;
    exists: boolean;
}

export class VoiceBackendService {
    private process: ChildProcess | null = null;
    private port = 58080;
    private outputChannel: vscode.OutputChannel;
    private statusBarItem: vscode.StatusBarItem;
    private lastError: string | null = null;
    private stdoutBuffer = '';
    private stderrBuffer = '';
    private _startingPromise: Promise<void> | null = null;
    private _terminalCreatedAt = 0;

    constructor() {
        this.outputChannel = vscode.window.createOutputChannel('OrbitScribe Voice');
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.statusBarItem.command = 'orbitscribe.restartVoiceBackend';
        this.updateStatusBar('unknown');
        this.statusBarItem.show();
    }

    /** Returns the last error message encountered during startup, or null. */
    getLastError(): string | null {
        return this.lastError;
    }

    private log(msg: string): void {
        const line = `[${new Date().toISOString()}] ${msg}`;
        console.log(`[OrbitScribe Voice] ${line}`);
        this.outputChannel.appendLine(line);
    }

    private updateStatusBar(state: 'online' | 'offline' | 'error' | 'unknown'): void {
        const icons: Record<string, string> = {
            online: '$(mic)',
            offline: '$(mute)',
            error: '$(warning)',
            unknown: '$(question)',
        };
        const texts: Record<string, string> = {
            online: 'Voice: Online',
            offline: 'Voice: Offline',
            error: 'Voice: Error',
            unknown: 'Voice: Unknown',
        };
        this.statusBarItem.text = `${icons[state]} ${texts[state]}`;
    }

    /** Build PYTHONPATH so the voice backend can find workspace modules like infinite_jukebox. */
    private getPythonPath(): string {
        const workspaceRoots = (vscode.workspace.workspaceFolders || []).map((f) => f.uri.fsPath);
        const extPath = this.getExtensionPath();
        const segments: string[] = [];
        // Prefer workspace roots (dev mode picks up latest changes)
        for (const root of workspaceRoots) {
            segments.push(root);
        }
        // Fallback to extension's own copy
        segments.push(path.join(extPath, 'voice-backend'));
        // Append existing PYTHONPATH if any
        if (process.env.PYTHONPATH) {
            segments.push(process.env.PYTHONPATH);
        }
        return segments.join(process.platform === 'win32' ? ';' : ':');
        this.statusBarItem.tooltip = 'Click to restart OrbitScribe Voice Backend';
    }

    /** Best-effort resolution of the extension root on disk. */
    private getExtensionPath(): string {
        const ext = vscode.extensions.getExtension('orbstudio.orbitscribe-swarm');
        if (ext) {
            return ext.extensionPath;
        }
        // Fallback heuristic based on typical out/ directory layout.
        return path.join(__dirname, '..', '..');
    }

    /**
     * Check whether a path exists, with a fallback for Windows App Execution Aliases
     * that cause fs.existsSync to return false even though the executable is valid.
     */
    private pathExists(filePath: string): boolean {
        if (fs.existsSync(filePath)) {
            return true;
        }
        try {
            fs.lstatSync(filePath);
            return true;
        } catch {
            return false;
        }
    }

    /** Resolve a command name to an absolute path using platform tools, then verify existence. */
    private resolveExecutableInPath(cmd: string): string | null {
        try {
            if (process.platform === 'win32') {
                const out = execSync(`where.exe "${cmd}"`, { encoding: 'utf-8', timeout: 5000 }).trim();
                const first = out.split(/\r?\n/)[0].trim();
                if (first && this.pathExists(first)) {
                    return first;
                }
            } else {
                const out = execSync(`sh -c "command -v \\"${cmd}\\""`, { encoding: 'utf-8', timeout: 5000 }).trim();
                if (out && this.pathExists(out)) {
                    return out;
                }
            }
        } catch {
            // Fall through to direct-path check.
        }
        // Allow absolute or relative paths that exist without PATH lookup.
        if (this.pathExists(cmd)) {
            return path.resolve(cmd);
        }
        return null;
    }

    /** Build the ordered list of Python candidates to try. */
    private getPythonCandidates(): PythonCandidate[] {
        const isWin = process.platform === 'win32';
        const candidates: PythonCandidate[] = [];

        // 1. User override from settings
        const configPath = vscode.workspace.getConfiguration('orbitscribe').get<string>('pythonPath', '');
        if (configPath && this.pathExists(configPath)) {
            candidates.push({ command: configPath, argsPrefix: [], resolvedPath: path.resolve(configPath) });
        }

        const pushIfResolved = (cmd: string, argsPrefix: string[] = []) => {
            const resolved = this.resolveExecutableInPath(cmd);
            candidates.push({ command: cmd, argsPrefix, resolvedPath: resolved });
        };

        if (isWin) {
            pushIfResolved('pythonw');
            pushIfResolved('python');
            pushIfResolved('py');
            // "py -3" is a special case: we need py.exe resolved, then pass -3 as arg.
            const pyPath = this.resolveExecutableInPath('py');
            if (pyPath) {
                candidates.push({ command: 'py', argsPrefix: ['-3'], resolvedPath: pyPath });
            } else {
                candidates.push({ command: 'py', argsPrefix: ['-3'], resolvedPath: null });
            }
            pushIfResolved('python3');

            // Hardcoded fallback paths common on Windows
            const hardcoded = [
                path.join(process.env.LOCALAPPDATA || '', 'Microsoft', 'WindowsApps', 'python.exe'),
                path.join(process.env.LOCALAPPDATA || '', 'Microsoft', 'WindowsApps', 'python3.exe'),
                path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python313', 'python.exe'),
                path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python312', 'python.exe'),
                path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python311', 'python.exe'),
                path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python310', 'python.exe'),
                path.join(process.env.LOCALAPPDATA || '', 'Programs', 'Python', 'Python39', 'python.exe'),
                path.join('C:', 'Python313', 'python.exe'),
                path.join('C:', 'Python312', 'python.exe'),
                path.join('C:', 'Python311', 'python.exe'),
                path.join('C:', 'Python310', 'python.exe'),
                path.join('C:', 'Python39', 'python.exe'),
                path.join(process.env.PROGRAMFILES || '', 'Python313', 'python.exe'),
                path.join(process.env.PROGRAMFILES || '', 'Python312', 'python.exe'),
                path.join(process.env.PROGRAMFILES || '', 'Python311', 'python.exe'),
                path.join(process.env.PROGRAMFILES || '', 'Python310', 'python.exe'),
                path.join(process.env.PROGRAMFILES || '', 'Python39', 'python.exe'),
            ];
            for (const p of hardcoded) {
                if (this.pathExists(p)) {
                    candidates.push({ command: p, argsPrefix: [], resolvedPath: path.resolve(p) });
                }
            }
        } else {
            pushIfResolved('python3');
            pushIfResolved('python');
            // Common Unix paths
            const unixPaths = ['/usr/bin/python3', '/usr/local/bin/python3', '/opt/homebrew/bin/python3'];
            for (const p of unixPaths) {
                if (this.pathExists(p)) {
                    candidates.push({ command: p, argsPrefix: [], resolvedPath: path.resolve(p) });
                }
            }
        }

        return candidates;
    }

    /** Build the ordered list of script paths to try. */
    private getScriptCandidates(): ScriptCandidate[] {
        const extPath = this.getExtensionPath();
        const candidates: string[] = [
            path.join(extPath, 'voice-backend', 'voice_to_text_web.py'),
            path.join(extPath, 'voice_to_text_web.py'),
            path.join(__dirname, '..', '..', 'voice-backend', 'voice_to_text_web.py'),
            path.join(__dirname, '..', '..', '..', 'voice_to_text_web.py'),
            path.join(__dirname, '..', '..', '..', '..', 'voice_to_text_web.py'),
        ];

        if (vscode.workspace.workspaceFolders) {
            for (const folder of vscode.workspace.workspaceFolders) {
                candidates.push(path.join(folder.uri.fsPath, 'voice_to_text_web.py'));
            }
        }

        return candidates.map((p) => ({ path: p, exists: fs.existsSync(p) }));
    }

    /** Find the first usable Python executable, verifying by actually running it. */
    private findPython(): { command: string; argsPrefix: string[]; resolvedPath: string } | null {
        for (const c of this.getPythonCandidates()) {
            if (!c.resolvedPath) {
                this.log(`Python candidate missing: ${c.command}${c.argsPrefix.length ? ' ' + c.argsPrefix.join(' ') : ''}`);
                continue;
            }
            try {
                const args = [...c.argsPrefix, '--version'];
                execSync(`"${c.resolvedPath}" ${args.join(' ')}`, { stdio: 'ignore', timeout: 3000 });
                this.log(`Python candidate OK: ${c.command}${c.argsPrefix.length ? ' ' + c.argsPrefix.join(' ') : ''} => ${c.resolvedPath}`);
                return { command: c.command, argsPrefix: c.argsPrefix, resolvedPath: c.resolvedPath };
            } catch {
                this.log(`Python candidate missing: ${c.command}${c.argsPrefix.length ? ' ' + c.argsPrefix.join(' ') : ''}`);
            }
        }
        return null;
    }

    /** Find the first usable script file, verifying existence. */
    private findScript(): string | null {
        for (const c of this.getScriptCandidates()) {
            if (c.exists) {
                this.log(`Script candidate OK: ${c.path}`);
                return c.path;
            }
            this.log(`Script candidate missing: ${c.path}`);
        }
        return null;
    }

    /** Runs a quick health check with a short timeout so polling is responsive. */
    private async isHealthyQuick(timeoutMs = 1500): Promise<boolean> {
        return new Promise((resolve) => {
            const timer = setTimeout(() => {
                try { req.destroy(); } catch { /* ignore */ }
                resolve(false);
            }, timeoutMs);

            const req = http.get(`http://127.0.0.1:${this.port}/api/status`, (res) => {
                clearTimeout(timer);
                resolve(res.statusCode !== undefined && res.statusCode >= 200 && res.statusCode < 300);
            });
            req.on('error', () => {
                clearTimeout(timer);
                resolve(false);
            });
        });
    }

    /** Public health check (used by callers, tolerant timeout). */
    async isHealthy(): Promise<boolean> {
        try {
            const resp = await httpGet(`http://127.0.0.1:${this.port}/api/status`);
            return resp.ok;
        } catch {
            return false;
        }
    }

    /** Runs a comprehensive diagnostic report. */
    async diagnose(): Promise<string[]> {
        const lines: string[] = [];
        lines.push('=== OrbitScribe Voice Backend Diagnostics ===');
        lines.push(`Platform: ${process.platform}`);
        lines.push(`Node version: ${process.version}`);
        lines.push(`VS Code version: ${vscode.version}`);
        lines.push(`Extension path: ${this.getExtensionPath()}`);
        lines.push('');

        lines.push('--- Python Detection ---');
        for (const c of this.getPythonCandidates()) {
            const label = `${c.command}${c.argsPrefix.length ? ' ' + c.argsPrefix.join(' ') : ''}`;
            if (c.resolvedPath && this.pathExists(c.resolvedPath)) {
                let ver = 'unknown';
                try {
                    const args = [...c.argsPrefix, '--version'];
                    ver = execSync(`"${c.resolvedPath}" ${args.join(' ')}`, { encoding: 'utf-8', timeout: 3000 }).trim();
                } catch (e: any) {
                    ver = `version check failed: ${e.message || e}`;
                }
                lines.push(`  ✅ ${label}: ${c.resolvedPath} (${ver})`);
            } else {
                lines.push(`  ❌ ${label}: not found in PATH`);
            }
        }
        lines.push('');

        lines.push('--- Script Path Detection ---');
        for (const c of this.getScriptCandidates()) {
            lines.push(`  ${c.exists ? '✅' : '❌'} ${c.path}`);
        }
        lines.push('');

        lines.push('--- Port Check ---');
        try {
            const resp = await httpGet(`http://127.0.0.1:${this.port}/api/status`);
            const data = await resp.json();
            lines.push(`  ✅ Port ${this.port} responds: ${JSON.stringify(data)}`);
        } catch (e: any) {
            lines.push(`  ❌ Port ${this.port} not responding: ${e.message || e}`);
        }
        lines.push('');

        lines.push('--- Process Status ---');
        if (this.process && !this.process.killed) {
            lines.push(`  ℹ️ Process PID: ${this.process.pid}, killed: ${this.process.killed}`);
        } else {
            lines.push(`  ❌ No active process`);
        }
        lines.push('');

        lines.push('--- Last Error ---');
        lines.push(this.lastError ? `  ❌ ${this.lastError}` : `  ✅ None`);
        lines.push('');

        lines.push('=== End Diagnostics ===');
        return lines;
    }

    /** Ensures the backend is running; starts it if necessary. */
    async ensureRunning(): Promise<void> {
        this.log('ensureRunning() called');
        if (await this.isHealthy()) {
            this.log('Voice backend already running');
            this.updateStatusBar('online');
            return;
        }

        // Deduplicate concurrent startup attempts -- like a contactor seal-in circuit:
        // once the coil energizes, all parallel pushbuttons are ignored until the cycle completes.
        if (this._startingPromise) {
            this.log('Voice backend startup already in progress -- waiting on existing promise');
            return this._startingPromise;
        }

        this._startingPromise = this._doEnsureRunning();
        try {
            await this._startingPromise;
        } finally {
            this._startingPromise = null;
        }
    }

    private async _doEnsureRunning(): Promise<void> {
        const mode = vscode.workspace.getConfiguration('orbitscribe').get<string>('voiceStartupMode', 'auto');

        try {
            if (mode === 'terminal') {
                await this.startViaTerminal();
            } else if (mode === 'spawn') {
                await this.start();
            } else {
                // auto: try spawn first, fall back to terminal
                try {
                    await this.start();
                } catch (err: any) {
                    this.log(`Spawn failed (${err.message}), trying terminal fallback...`);
                    await this.startViaTerminal();
                }
            }
            this.updateStatusBar('online');
            vscode.window.showInformationMessage('✅ Voice Backend is online.');
        } catch (err: any) {
            this.updateStatusBar('error');
            const msg = err.message || String(err);
            this.lastError = msg;
            this.log(`Failed to start voice backend: ${msg}`);
            vscode.window.showErrorMessage(`❌ Voice Backend failed: ${msg}. Run "OrbitScribe: Diagnose Voice Backend" for details.`);
            throw err;
        }
    }

    /** Starts the voice backend process and waits for health check or early exit. */
    async start(): Promise<void> {
        this.lastError = null;
        this.stdoutBuffer = '';
        this.stderrBuffer = '';

        // 1. Resolve script
        const scriptPath = this.findScript();
        if (!scriptPath) {
            const searched = this.getScriptCandidates().map((c) => c.path).join('\n  ');
            const err = `voice_to_text_web.py not found. Searched:\n  ${searched}`;
            this.log(err);
            throw new Error(err);
        }

        // 2. Resolve Python
        const python = this.findPython();
        if (!python) {
            const tried = this.getPythonCandidates()
                .map((c) => `${c.command}${c.argsPrefix.length ? ' ' + c.argsPrefix.join(' ') : ''}`)
                .join(', ');
            const err = `No Python executable found. Tried: ${tried}`;
            this.log(err);
            throw new Error(err);
        }

        // 3. Verify both exist (defense-in-depth)
        if (!this.pathExists(python.resolvedPath)) {
            const err = `Python executable does not exist: ${python.resolvedPath}`;
            this.log(err);
            throw new Error(err);
        }
        if (!this.pathExists(scriptPath)) {
            const err = `Script file does not exist: ${scriptPath}`;
            this.log(err);
            throw new Error(err);
        }

        // 4. Spawn with shell: false and windowsHide: true
        const args = [...python.argsPrefix, scriptPath];
        const cwd = path.dirname(scriptPath);
        this.log(`Spawning: ${python.resolvedPath} ${args.map((a) => `"${a}"`).join(' ')} (cwd: ${cwd})`);

        let proc: ChildProcess;
        try {
            proc = spawn(python.resolvedPath, args, {
                cwd,
                detached: true,
                shell: false,
                windowsHide: true,
                stdio: ['ignore', 'pipe', 'pipe'],
                env: {
                    ...process.env,
                    ORBITSCRIBE_NO_BROWSER: '1',
                    ORBITSCRIBE_EXTENSION_MODE: '1',
                    PYTHONPATH: this.getPythonPath(),
                },
            });
        } catch (spawnErr: any) {
            const err = `Synchronous spawn error: ${spawnErr.message || spawnErr}`;
            this.log(err);
            throw new Error(err);
        }

        this.process = proc;

        // 5. Capture stdout/stderr into rolling buffers for post-mortem diagnosis
        proc.stdout?.on('data', (data: Buffer) => {
            const text = data.toString('utf-8');
            this.stdoutBuffer += text;
            this.log(`[stdout] ${text.trimEnd()}`);
        });

        proc.stderr?.on('data', (data: Buffer) => {
            const text = data.toString('utf-8');
            this.stderrBuffer += text;
            this.log(`[stderr] ${text.trimEnd()}`);
        });

        const spawnTime = Date.now();
        const healthCheckTimeout = 15000; // 15s total startup budget

        return new Promise((resolve, reject) => {
            let settled = false;

            const cleanup = () => {
                settled = true;
            };

            const onExit = (code: number | null, signal: NodeJS.Signals | null) => {
                const elapsed = Date.now() - spawnTime;
                const output = (this.stdoutBuffer + this.stderrBuffer).trim();

                let reason = `Process exited with code=${code}, signal=${signal}`;
                if (code === null && signal === null) {
                    reason = 'Process failed to spawn (possible Windows Security / antivirus block, or missing DLL)';
                }
                if (output) {
                    reason += `\n\nCaptured output:\n${output}`;
                }

                this.log(`Process exited after ${elapsed}ms: ${reason}`);
                this.process = null;
                this.updateStatusBar('offline');

                if (!settled) {
                    cleanup();
                    this.lastError = reason;
                    reject(new Error(reason));
                }
            };

            const onError = (err: Error) => {
                this.log(`Process error event: ${err.message}`);
                if (!settled) {
                    cleanup();
                    this.lastError = err.message;
                    reject(new Error(`Failed to spawn voice backend: ${err.message}`));
                }
            };

            proc.on('exit', onExit);
            proc.on('error', onError);

            // 6. Poll health check until success, timeout, or early exit
            const poll = async () => {
                if (settled) {
                    return;
                }

                const elapsed = Date.now() - spawnTime;
                if (elapsed >= healthCheckTimeout) {
                    cleanup();
                    const err = `Voice backend failed to start within ${healthCheckTimeout / 1000} seconds`;
                    this.log(err);
                    reject(new Error(err));
                    return;
                }

                try {
                    const healthy = await this.isHealthyQuick(1500);
                    if (healthy && !settled) {
                        cleanup();
                        this.log('Voice backend health check passed');
                        resolve();
                        return;
                    }
                } catch {
                    // ignore
                }

                setTimeout(poll, 400);
            };

            poll();
        });
    }

    /** Starts the voice backend via VS Code integrated terminal (fallback when spawn is blocked). */
    async startViaTerminal(): Promise<void> {
        this.lastError = null;
        const scriptPath = this.findScript();
        const python = this.findPython();

        if (!scriptPath) {
            throw new Error('voice_to_text_web.py not found');
        }
        if (!python) {
            throw new Error('No Python executable found');
        }

        this.log(`Starting voice backend via terminal: ${python.resolvedPath} "${scriptPath}"`);

        // Reuse or create terminal
        let terminal = vscode.window.terminals.find(t => t.name === 'OrbitScribe Voice');
        let isFreshTerminal = false;
        if (!terminal) {
            terminal = vscode.window.createTerminal({
                name: 'OrbitScribe Voice',
                cwd: path.dirname(scriptPath),
            });
            this._terminalCreatedAt = Date.now();
            isFreshTerminal = true;
        }

        // Guard against rapid duplicate commands in the same terminal -- like a mechanical
        // interlock that prevents closing a breaker twice within the same second.
        const terminalAgeMs = Date.now() - this._terminalCreatedAt;
        if (isFreshTerminal || terminalAgeMs >= 10000) {
            const pyPath = this.getPythonPath();
            const cmd = process.platform === 'win32'
                ? `$env:ORBITSCRIBE_NO_BROWSER="1"; $env:ORBITSCRIBE_EXTENSION_MODE="1"; $env:PYTHONPATH="${pyPath}"; & "${python.resolvedPath}" "${scriptPath}"`
                : `PYTHONPATH="${pyPath}" ORBITSCRIBE_NO_BROWSER=1 ORBITSCRIBE_EXTENSION_MODE=1 "${python.resolvedPath}" "${scriptPath}"`;
            terminal.sendText(cmd);
            terminal.show(true);
        } else {
            this.log('Terminal already exists and was created recently -- skipping duplicate command');
        }

        const healthCheckTimeout = 15000;
        const spawnTime = Date.now();
        while (Date.now() - spawnTime < healthCheckTimeout) {
            await new Promise(r => setTimeout(r, 500));
            if (await this.isHealthyQuick(1500)) {
                this.log('Voice backend health check passed (terminal)');
                return;
            }
        }
        throw new Error('Voice backend failed to start within 15 seconds (terminal mode)');
    }

    stop(): void {
        if (this.process && !this.process.killed) {
            this.log('Stopping voice backend (spawn)');
            this.process.kill();
            this.process = null;
        }
        const terminal = vscode.window.terminals.find(t => t.name === 'OrbitScribe Voice');
        if (terminal) {
            try { terminal.dispose(); } catch {}
        }
        this.updateStatusBar('offline');
    }

    dispose(): void {
        this.stop();
        this.statusBarItem.dispose();
        this.outputChannel.dispose();
    }
}
