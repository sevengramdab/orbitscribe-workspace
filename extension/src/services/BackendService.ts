import * as vscode from 'vscode';
import { spawn, ChildProcess, execSync } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as net from 'net';
import { httpGet } from './httpUtil';

export class BackendService {
    private process: ChildProcess | null = null;
    private port: number;
    private outputChannel: vscode.OutputChannel;
    private watchdogTimer: NodeJS.Timeout | null = null;
    private restartAttempts: number = 0;
    private readonly maxRestartAttempts: number = 5;
    private readonly watchdogIntervalMs: number = 10000;
    private readonly restartBackoffMs: number = 5000;
    private readonly portScanRange: number = 10;
    private _onStatusChange = new vscode.EventEmitter<{ online: boolean; ollama: boolean; model: string }>();
    readonly onStatusChange = this._onStatusChange.event;

    constructor() {
        const config = vscode.workspace.getConfiguration('orbitscribe');
        this.port = config.get<number>('backendPort', 58081);
        this.outputChannel = vscode.window.createOutputChannel('OrbitScribe');
        this.startWatchdog();
    }

    private startWatchdog(): void {
        if (this.watchdogTimer) {
            clearInterval(this.watchdogTimer);
        }
        this.watchdogTimer = setInterval(async () => {
            await this.pollStatus();
        }, this.watchdogIntervalMs);
    }

    private async pollStatus(): Promise<void> {
        const backendOk = await this.isHealthy();
        const ollamaOk = await this.checkOllama();
        let model = 'unknown';
        if (backendOk) {
            try {
                const resp = await httpGet(`http://127.0.0.1:${this.port}/api/settings`);
                if (resp.ok) {
                    const data = await resp.json();
                    model = data.local_model || data.orchestrator_model || 'unknown';
                }
            } catch { /* ignore */ }
        }

        this._onStatusChange.fire({ online: backendOk, ollama: ollamaOk, model });

        if (!backendOk && this.process === null && this.restartAttempts < this.maxRestartAttempts) {
            console.log('[OrbitScribe] Watchdog: backend offline, attempting restart...');
            this.outputChannel.appendLine('[Watchdog] Backend offline — auto-restarting...');
            try {
                await this.ensureRunning();
                this.restartAttempts = 0;
            } catch (err: any) {
                this.restartAttempts++;
                const msg = `Auto-restart failed (${this.restartAttempts}/${this.maxRestartAttempts}): ${err.message || err}`;
                console.error(msg);
                this.outputChannel.appendLine(`[Watchdog] ${msg}`);
            }
        }
    }

    async ensureRunning(): Promise<void> {
        if (await this.isHealthy()) {
            console.log('Backend already running');
            return;
        }

        vscode.window.showInformationMessage('🐝 Starting OrbitScribe Backend...');
        try {
            await this.start();
            vscode.window.showInformationMessage('✅ Backend is online.');
        } catch (err: any) {
            vscode.window.showErrorMessage(`❌ Backend failed to start: ${err.message || err}`);
            throw err;
        }
    }

    async isHealthy(): Promise<boolean> {
        try {
            const resp = await httpGet(`http://127.0.0.1:${this.port}/api/health`);
            return resp.ok;
        } catch {
            return false;
        }
    }

    async checkOllama(): Promise<boolean> {
        try {
            const resp = await httpGet('http://127.0.0.1:11434/api/tags');
            return resp.ok;
        } catch {
            return false;
        }
    }

    private async isPortInUse(port: number): Promise<boolean> {
        return new Promise((resolve) => {
            const server = net.createServer();
            server.once('error', (err: any) => {
                if (err.code === 'EADDRINUSE') {
                    resolve(true);
                } else {
                    resolve(false);
                }
            });
            server.once('listening', () => {
                server.close();
                resolve(false);
            });
            server.listen(port, '127.0.0.1');
        });
    }

    private killProcessOnPort(port: number): boolean {
        try {
            if (process.platform === 'win32') {
                const netstat = execSync(`netstat -ano | findstr :${port}`, { encoding: 'utf-8', timeout: 5000 });
                const lines = netstat.split(/\r?\n/).filter(l => l.trim());
                for (const line of lines) {
                    const parts = line.trim().split(/\s+/);
                    const pid = parts[parts.length - 1];
                    if (pid && /^\d+$/.test(pid)) {
                        try {
                            const tasklist = execSync(`tasklist /FI "PID eq ${pid}" /FO CSV /NH`, { encoding: 'utf-8', timeout: 3000 });
                            if (tasklist.toLowerCase().includes('python')) {
                                console.log(`[OrbitScribe] Killing stale python.exe on port ${port} (PID ${pid})`);
                                this.outputChannel.appendLine(`[PortGuard] Killing stale python.exe on port ${port} (PID ${pid})`);
                                execSync(`taskkill /F /PID ${pid}`, { timeout: 3000 });
                                return true;
                            }
                        } catch { /* ignore */ }
                    }
                }
            } else {
                const lsof = execSync(`lsof -ti :${port}`, { encoding: 'utf-8', timeout: 5000 });
                const pids = lsof.trim().split(/\r?\n/).filter(l => l.trim());
                for (const pid of pids) {
                    console.log(`[OrbitScribe] Killing stale process on port ${port} (PID ${pid})`);
                    this.outputChannel.appendLine(`[PortGuard] Killing stale process on port ${port} (PID ${pid})`);
                    execSync(`kill -9 ${pid}`, { timeout: 3000 });
                }
                return pids.length > 0;
            }
        } catch {
            // No process found or command failed
        }
        return false;
    }

    private async findFreePort(startPort: number): Promise<number> {
        for (let p = startPort; p < startPort + this.portScanRange; p++) {
            if (!(await this.isPortInUse(p))) {
                return p;
            }
        }
        throw new Error(`No free port found in range ${startPort}-${startPort + this.portScanRange - 1}`);
    }

    private async resolvePortConflict(): Promise<void> {
        const desiredPort = this.port;
        if (await this.isPortInUse(desiredPort)) {
            // Try to kill a stale python backend on that port
            const killed = this.killProcessOnPort(desiredPort);
            if (killed) {
                // Give the OS a moment to release the port
                await new Promise(r => setTimeout(r, 1000));
                if (!(await this.isPortInUse(desiredPort))) {
                    console.log(`[OrbitScribe] Port ${desiredPort} freed after killing stale process`);
                    this.outputChannel.appendLine(`[PortGuard] Port ${desiredPort} freed.`);
                    return;
                }
            }
            // Fall back to scanning for a free port
            const freePort = await this.findFreePort(desiredPort + 1);
            console.log(`[OrbitScribe] Port ${desiredPort} in use by foreign process. Switching to port ${freePort}`);
            this.outputChannel.appendLine(`[PortGuard] Port ${desiredPort} occupied. Using fallback port ${freePort}.`);
            this.port = freePort;
        }
    }

    async start(): Promise<void> {
        await this.resolvePortConflict();

        const mainPath = this.findBackendMain();
        const backendPath = path.dirname(mainPath);
        const python = this.findPython();

        if (!fs.existsSync(mainPath)) {
            throw new Error(`Backend main.py not found at: ${mainPath}`);
        }

        const msg = `[OrbitScribe] Starting backend: ${python} ${mainPath} (port ${this.port})`;
        console.log(msg);
        this.outputChannel.appendLine(msg);

        const env = process.env;
        env['SWARM_PORT'] = String(this.port);

        // Buffer recent stderr for crash diagnostics
        const stderrBuffer: string[] = [];
        const maxStderrLines = 20;

        this.process = spawn(python, [mainPath], {
            cwd: backendPath,
            detached: true,
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,
            env,
        });

        this.process.stdout?.on('data', (data) => {
            const line = `[Backend] ${data}`;
            console.log(line);
            this.outputChannel.appendLine(line);
        });

        this.process.stderr?.on('data', (data) => {
            const text = data.toString();
            const line = `[Backend] ${text}`;
            console.error(line);
            this.outputChannel.appendLine(line);
            // Keep last N lines for diagnostics
            stderrBuffer.push(...text.split(/\r?\n/).filter((l: string) => l.trim()));
            while (stderrBuffer.length > maxStderrLines) {
                stderrBuffer.shift();
            }
        });

        let exitCode: number | null = null;
        this.process.on('exit', (code) => {
            exitCode = code;
            const line = `[Backend] exited with code ${code}`;
            console.log(line);
            this.outputChannel.appendLine(line);
            this.process = null;
        });

        this.process.on('error', (err) => {
            const line = `[Backend] spawn error: ${err.message}`;
            console.error(line);
            this.outputChannel.appendLine(line);
        });

        // Wait for it to come online with smarter probing
        const maxWaitMs = 20000;
        const intervalMs = 500;
        const startTime = Date.now();
        while (Date.now() - startTime < maxWaitMs) {
            await new Promise(r => setTimeout(r, intervalMs));

            // Success path
            if (await this.isHealthy()) {
                console.log('Backend started successfully');
                return;
            }

            // Failure path: process died during startup
            if (this.process === null && exitCode !== null) {
                const stderrSummary = stderrBuffer.join('\n');
                // Detect common failure modes
                if (stderrSummary.includes('Address already in use') || stderrSummary.includes('Only one usage of each socket address')) {
                    throw new Error(`Backend crashed: port ${this.port} is already in use.\n${stderrSummary}`);
                }
                if (stderrSummary.includes('ModuleNotFoundError') || stderrSummary.includes('ImportError')) {
                    throw new Error(`Backend crashed: missing Python dependency.\n${stderrSummary}`);
                }
                throw new Error(`Backend crashed with exit code ${exitCode}.\nLast stderr:\n${stderrSummary}`);
            }
        }

        // Timeout path — try to scrape a diagnosis from stderr
        const stderrSummary = stderrBuffer.join('\n');
        if (stderrSummary.includes('Address already in use') || stderrSummary.includes('Only one usage of each socket address')) {
            throw new Error(`Backend failed to start: port ${this.port} conflict detected.\n${stderrSummary}`);
        }
        throw new Error(`Backend failed to start within ${maxWaitMs / 1000} seconds.\nLast stderr:\n${stderrSummary || '(none)'}`);
    }

    private findBackendMain(): string {
        // Strategy 1: bundled inside extension (production)
        const bundled = path.join(__dirname, '..', '..', 'swarm-backend', 'main.py');
        if (fs.existsSync(bundled)) {
            return bundled;
        }

        // Strategy 2: development mode — extension/src/services/BackendService.ts
        // __dirname = extension/out/services/
        const devCandidate = path.join(__dirname, '..', '..', '..', 'swarm-backend', 'main.py');
        if (fs.existsSync(devCandidate)) {
            return devCandidate;
        }

        // Strategy 3: sibling to extension folder
        const siblingCandidate = path.join(__dirname, '..', '..', '..', '..', 'swarm-backend', 'main.py');
        if (fs.existsSync(siblingCandidate)) {
            return siblingCandidate;
        }

        // Fallback
        return bundled;
    }

    private findPython(): string {
        // On Windows, prefer pythonw (no console window, less AV scrutiny)
        const candidates = process.platform === 'win32'
            ? ['pythonw', 'python', 'py', 'python3']
            : ['python3', 'python'];

        for (const py of candidates) {
            try {
                execSync(`${py} --version`, { stdio: 'ignore', timeout: 3000 });
                // Resolve to absolute path so spawn() always works, even when
                // the Extension Host has a different PATH view than execSync.
                if (process.platform === 'win32') {
                    const out = execSync(`where.exe "${py}"`, { encoding: 'utf-8', timeout: 3000 }).trim();
                    const first = out.split(/\r?\n/)[0].trim();
                    if (first) { return first; }
                } else {
                    const out = execSync(`sh -c "command -v \\"${py}\\""`, { encoding: 'utf-8', timeout: 3000 }).trim();
                    if (out) { return out; }
                }
                return py;
            } catch {
                // try next
            }
        }

        // Last resort: try to return a user-configured absolute path
        const configPath = vscode.workspace.getConfiguration('orbitscribe').get<string>('pythonPath', '');
        if (configPath) {
            return configPath;
        }

        throw new Error('No Python executable found. Tried: ' + candidates.join(', '));
    }

    stop(): void {
        if (this.watchdogTimer) {
            clearInterval(this.watchdogTimer);
            this.watchdogTimer = null;
        }
        if (this.process && !this.process.killed) {
            this.process.kill();
            this.process = null;
        }
    }

    getBaseUrl(): string {
        return `http://127.0.0.1:${this.port}`;
    }
}
