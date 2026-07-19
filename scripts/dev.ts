import { createConnection } from 'node:net';
import { join } from 'node:path';

const HOST = '127.0.0.1';
const WEB_PORT = 9000;
const API_PORT = 9001;
const REPOSITORY_ROOT = join(import.meta.dir, '..');
const FRONTEND_DIRECTORY = join(REPOSITORY_ROOT, 'frontend');

type TSignal = 'SIGINT' | 'SIGTERM';

const isPortInUse = (port: number): Promise<boolean> => {
  return new Promise((resolve) => {
    const socket = createConnection({ host: HOST, port });
    let settled = false;

    const finish = (inUse: boolean): void => {
      if (settled) {
        return;
      }
      settled = true;
      socket.destroy();
      resolve(inUse);
    };

    socket.setTimeout(500);
    socket.once('connect', () => finish(true));
    socket.once('error', () => finish(false));
    socket.once('timeout', () => finish(false));
  });
};

const verifyPorts = async (): Promise<boolean> => {
  const ports = [WEB_PORT, API_PORT];
  const states = await Promise.all(ports.map(isPortInUse));
  const occupiedPorts = ports.filter((_, index) => states[index]);

  if (occupiedPorts.length === 0) {
    return true;
  }

  console.error(`Cannot start development: port${occupiedPorts.length === 1 ? '' : 's'} ${occupiedPorts.join(', ')} already in use.`);
  console.error('Stop the existing process and run the command again.');
  return false;
};

const runRouteGeneration = async (): Promise<number> => {
  const routeProcess = Bun.spawn({
    cmd: [process.execPath, 'run', 'routes:generate'],
    cwd: FRONTEND_DIRECTORY,
    env: process.env,
    stdin: 'inherit',
    stdout: 'inherit',
    stderr: 'inherit',
  });

  return routeProcess.exited;
};

const stopProcess = (childProcess: Bun.Subprocess, signal: TSignal): void => {
  try {
    childProcess.kill(signal);
  } catch {
    // The process may have exited between status inspection and signal delivery.
  }
};

const resolvePythonExecutable = (): string => {
  if (process.env.RELEASE_ASSURANCE_PYTHON) {
    return process.env.RELEASE_ASSURANCE_PYTHON;
  }

  if (process.env.VIRTUAL_ENV) {
    const executable = process.platform === 'win32' ? 'python.exe' : 'python';
    const directory = process.platform === 'win32' ? 'Scripts' : 'bin';
    return join(process.env.VIRTUAL_ENV, directory, executable);
  }

  return 'python';
};

const runDevelopment = async (environmentOverrides: Record<string, string> = {}): Promise<number> => {
  if (!(await verifyPorts())) {
    return 1;
  }

  const routeStatus = await runRouteGeneration();
  if (routeStatus !== 0) {
    return routeStatus;
  }

  const environment = { ...process.env, ...environmentOverrides };
  const apiProcess = Bun.spawn({
    cmd: [resolvePythonExecutable(), '-m', 'uvicorn', 'app.main:app', '--app-dir', 'backend', '--host', HOST, '--port', String(API_PORT)],
    cwd: REPOSITORY_ROOT,
    env: environment,
    stdin: 'inherit',
    stdout: 'inherit',
    stderr: 'inherit',
  });
  const webProcess = Bun.spawn({
    cmd: [
      process.execPath,
      join(FRONTEND_DIRECTORY, 'node_modules', 'vite', 'bin', 'vite.js'),
      '--host',
      HOST,
      '--port',
      String(WEB_PORT),
      '--strictPort',
    ],
    cwd: FRONTEND_DIRECTORY,
    env: environment,
    stdin: 'inherit',
    stdout: 'inherit',
    stderr: 'inherit',
  });
  const childProcesses = [apiProcess, webProcess];
  let interrupted = false;

  const stopAll = (signal: TSignal): void => {
    interrupted = true;
    for (const childProcess of childProcesses) {
      stopProcess(childProcess, signal);
    }
  };
  const handleInterrupt = (): void => stopAll('SIGINT');
  const handleTermination = (): void => stopAll('SIGTERM');

  process.once('SIGINT', handleInterrupt);
  process.once('SIGTERM', handleTermination);

  try {
    const firstExit = await Promise.race([
      apiProcess.exited.then((status) => ({ name: 'API', status })),
      webProcess.exited.then((status) => ({ name: 'web', status })),
    ]);

    if (!interrupted) {
      console.error(`${firstExit.name} process exited with status ${firstExit.status}; stopping development runtime.`);
      for (const childProcess of childProcesses) {
        stopProcess(childProcess, 'SIGTERM');
      }
    }

    await Promise.allSettled(childProcesses.map((childProcess) => childProcess.exited));
    return interrupted ? 0 : firstExit.status;
  } finally {
    process.off('SIGINT', handleInterrupt);
    process.off('SIGTERM', handleTermination);
  }
};

export { resolvePythonExecutable, runDevelopment };

if (import.meta.main) {
  process.exitCode = await runDevelopment();
}
