import * as vscode from 'vscode';
import { spawn, ChildProcess, execSync } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

export class BackendService {
    private process: ChildProcess | null = null;
    private port: number;

    constructor() {
        const config = vscode.workspace.getConfiguration('orbitscribe');
        this.port = config.get<number>('backendPort', 58081);
    }

    async ensureRunning(): Promise<void> {
        if (await this.isHealthy()) {
            console.log('Swarm backend already running');
            return;
        }

        vscode.window.showInformationMessage('🐝 Starting OrbitScribe Swarm Backend...');
        try {
            await this.start();
            vscode.window.showInformationMessage('✅ Swarm Backend is online.');
        } catch (err) {
            vscode.window.showErrorMessage(`❌ Swarm Backend failed to start: ${err}`);
            throw err;
        }
    }

    async isHealthy(): Promise<boolean> {
        try {
            const resp = await fetch(`http://127.0.0.1:${this.port}/api/health`, { method: 'GET' });
            return resp.ok;
        } catch {
            return false;
        }
    }

    async checkOllama(): Promise<boolean> {
        try {
            const resp = await fetch('http://127.0.0.1:11434/api/tags', { method: 'GET' });
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

        console.log(`[OrbitScribe] Starting backend: ${python} ${mainPath}`);

        this.process = spawn(python, [mainPath], {
            cwd: backendPath,
            detached: false,
            stdio: ['ignore', 'pipe', 'pipe'],
        });

        this.process.stdout?.on('data', (data) => {
            console.log(`[Swarm Backend] ${data}`);
        });

        this.process.stderr?.on('data', (data) => {
            console.error(`[Swarm Backend] ${data}`);
        });

        this.process.on('exit', (code) => {
            console.log(`[Swarm Backend] exited with code ${code}`);
            this.process = null;
        });

        // Wait for it to come online
        for (let i = 0; i < 20; i++) {
            await new Promise(r => setTimeout(r, 500));
            if (await this.isHealthy()) {
                console.log('Swarm backend started successfully');
                return;
            }
        }

        throw new Error('Swarm backend failed to start within 10 seconds');
    }

    private findBackendMain(): string {
        // Strategy 1: extension is installed (production)
        const ext = vscode.extensions.getExtension('orbstudio.orbitscribe-swarm');
        if (ext) {
            const candidate = path.join(ext.extensionPath, 'swarm-backend', 'main.py');
            if (fs.existsSync(candidate)) {
                return candidate;
            }
        }

        // Strategy 2: development mode — extension/src/services/BackendService.ts
        // __dirname = extension/out/services/
        const devCandidate = path.join(__dirname, '..', '..', 'swarm-backend', 'main.py');
        if (fs.existsSync(devCandidate)) {
            return devCandidate;
        }

        // Strategy 3: sibling to extension folder
        const siblingCandidate = path.join(__dirname, '..', '..', '..', 'swarm-backend', 'main.py');
        if (fs.existsSync(siblingCandidate)) {
            return siblingCandidate;
        }

        // Fallback — will likely error but gives a concrete path in the message
        return devCandidate;
    }

    private findPython(): string {
        if (process.platform === 'win32') {
            try {
                execSync('python --version', { stdio: 'ignore' });
                return 'python';
            } catch {
                try {
                    execSync('py --version', { stdio: 'ignore' });
                    return 'py';
                } catch {
                    return 'python';
                }
            }
        }
        return 'python3';
    }

    stop(): void {
        if (this.process && !this.process.killed) {
            this.process.kill();
            this.process = null;
        }
    }

    getBaseUrl(): string {
        return `http://127.0.0.1:${this.port}`;
    }
}
