import * as vscode from 'vscode';
import { spawn, ChildProcess, execSync } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
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

    async start(): Promise<void> {
        const mainPath = this.findBackendMain();
        const backendPath = path.dirname(mainPath);
        const python = this.findPython();

        if (!fs.existsSync(mainPath)) {
            throw new Error(`Backend main.py not found at: ${mainPath}`);
        }

        const msg = `[OrbitScribe] Starting backend: ${python} ${mainPath}`;
        console.log(msg);
        this.outputChannel.appendLine(msg);

        this.process = spawn(python, [mainPath], {
            cwd: backendPath,
            detached: true,
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,
        });

        this.process.stdout?.on('data', (data) => {
            const line = `[Backend] ${data}`;
            console.log(line);
            this.outputChannel.appendLine(line);
        });

        this.process.stderr?.on('data', (data) => {
            const line = `[Backend] ${data}`;
            console.error(line);
            this.outputChannel.appendLine(line);
        });

        this.process.on('exit', (code) => {
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

        // Wait for it to come online
        for (let i = 0; i < 30; i++) {
            await new Promise(r => setTimeout(r, 500));
            if (await this.isHealthy()) {
                console.log('Backend started successfully');
                return;
            }
        }

        throw new Error('Backend failed to start within 15 seconds');
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
