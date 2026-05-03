import * as vscode from 'vscode';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';

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

        await this.start();
    }

    async isHealthy(): Promise<boolean> {
        try {
            const resp = await fetch(`http://127.0.0.1:${this.port}/api/health`, { method: 'GET' });
            return resp.ok;
        } catch {
            return false;
        }
    }

    async start(): Promise<void> {
        // Find the swarm-backend directory relative to extension
        const extPath = vscode.extensions.getExtension('orbstudio.orbitscribe-swarm')?.extensionPath
            || path.join(__dirname, '..', '..', 'swarm-backend');
        const backendPath = path.join(extPath, 'swarm-backend');
        const mainPath = path.join(backendPath, 'main.py');

        // Try to find Python
        const python = process.platform === 'win32' ? 'python' : 'python3';

        console.log(`Starting swarm backend: ${python} ${mainPath}`);

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
