import { defineConfig, devices } from '@playwright/test';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const backendRoot = path.resolve(frontendRoot, '../backend');
const ownsTempRoot = !process.env.LEXILEARN_PLAYWRIGHT_ROOT;
const isolatedRoot = process.env.LEXILEARN_PLAYWRIGHT_ROOT
  || fs.mkdtempSync(path.join(os.tmpdir(), 'lexilearn-playwright-'));
process.env.LEXILEARN_PLAYWRIGHT_ROOT = isolatedRoot;

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      server.close(error => error ? reject(error) : resolve(port));
    });
  });
}

const frontendPort = Number(process.env.LEXILEARN_PLAYWRIGHT_FRONTEND_PORT || await freePort());
const backendPort = Number(process.env.LEXILEARN_PLAYWRIGHT_BACKEND_PORT || await freePort());
process.env.LEXILEARN_PLAYWRIGHT_FRONTEND_PORT = String(frontendPort);
process.env.LEXILEARN_PLAYWRIGHT_BACKEND_PORT = String(backendPort);
const frontendUrl = `http://127.0.0.1:${frontendPort}`;
const backendUrl = `http://127.0.0.1:${backendPort}`;
const testStorage = path.join(isolatedRoot, 'storage');
const backendEnv = {
  ...process.env,
  DATABASE_URL: `sqlite:///${path.join(isolatedRoot, 'test.db')}`,
  STORAGE_DIR: testStorage,
  TEACHER_ACCESS_CODE: 'playwright-teacher-code',
  CORS_ORIGINS: frontendUrl,
  STT_PROVIDER: 'mock',
  LLM_PROVIDER: 'mock',
  GROQ_API_KEY: '',
  GOOGLE_API_KEY: '',
  R2_ENDPOINT_URL: '',
  R2_ACCESS_KEY_ID: '',
  R2_SECRET_ACCESS_KEY: '',
  WHISPER_PRELOAD: 'false',
};

if (ownsTempRoot) {
  process.once('exit', () => fs.rmSync(isolatedRoot, { recursive: true, force: true }));
}

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: frontendUrl,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'],
        },
      },
    },
  ],
  webServer: [
    {
      command: `./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port ${backendPort}`,
      cwd: backendRoot,
      url: `${backendUrl}/health`,
      env: backendEnv,
      reuseExistingServer: false,
      timeout: 120000,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort} --strictPort`,
      cwd: frontendRoot,
      url: frontendUrl,
      env: { ...process.env, VITE_API_PROXY_TARGET: backendUrl },
      reuseExistingServer: false,
      timeout: 120000,
    },
  ],
});
