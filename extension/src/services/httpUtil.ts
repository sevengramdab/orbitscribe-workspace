import * as http from 'http';

export function httpGet(url: string): Promise<{ ok: boolean; status: number; json: () => Promise<any>; text: () => Promise<string> }> {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
            req.destroy();
            reject(new Error('Request timeout'));
        }, 5000);

        const req = http.get(url, (res) => {
            clearTimeout(timer);
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                resolve({
                    ok: res.statusCode! >= 200 && res.statusCode! < 300,
                    status: res.statusCode!,
                    text: () => Promise.resolve(data),
                    json: () => Promise.resolve(JSON.parse(data)),
                });
            });
        });
        req.on('error', (err) => {
            clearTimeout(timer);
            reject(err);
        });
    });
}

export function httpPost(url: string, body?: object): Promise<{ ok: boolean; status: number; json: () => Promise<any>; text: () => Promise<string> }> {
    return new Promise((resolve, reject) => {
        const parsed = new URL(url);
        const postData = body ? JSON.stringify(body) : '';
        const options: http.RequestOptions = {
            hostname: parsed.hostname,
            port: parsed.port,
            path: parsed.pathname + parsed.search,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData),
            },
        };

        const timer = setTimeout(() => {
            req.destroy();
            reject(new Error('Request timeout'));
        }, 5000);

        const req = http.request(options, (res) => {
            clearTimeout(timer);
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                resolve({
                    ok: res.statusCode! >= 200 && res.statusCode! < 300,
                    status: res.statusCode!,
                    text: () => Promise.resolve(data),
                    json: () => Promise.resolve(JSON.parse(data)),
                });
            });
        });
        req.on('error', (err) => {
            clearTimeout(timer);
            reject(err);
        });
        if (postData) {
            req.write(postData);
        }
        req.end();
    });
}

export function httpDelete(url: string): Promise<{ ok: boolean; status: number; json: () => Promise<any>; text: () => Promise<string> }> {
    return new Promise((resolve, reject) => {
        const parsed = new URL(url);
        const options: http.RequestOptions = {
            hostname: parsed.hostname,
            port: parsed.port,
            path: parsed.pathname + parsed.search,
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const timer = setTimeout(() => {
            req.destroy();
            reject(new Error('Request timeout'));
        }, 5000);

        const req = http.request(options, (res) => {
            clearTimeout(timer);
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => {
                resolve({
                    ok: res.statusCode! >= 200 && res.statusCode! < 300,
                    status: res.statusCode!,
                    text: () => Promise.resolve(data),
                    json: () => Promise.resolve(JSON.parse(data)),
                });
            });
        });
        req.on('error', (err) => {
            clearTimeout(timer);
            reject(err);
        });
        req.end();
    });
}
