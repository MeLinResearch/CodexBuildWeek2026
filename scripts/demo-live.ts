import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { resolvePythonExecutable, runDevelopment } from './dev';
import { resolveCommandInvocation } from './executable';

const verifyCommand = async (command: string[]): Promise<boolean> => {
  try {
    const commandProcess = Bun.spawn({
      cmd: command,
      stdin: 'ignore',
      stdout: command.at(-1) === '--version' ? 'inherit' : 'ignore',
      stderr: command.at(-1) === '--version' ? 'inherit' : 'ignore',
    });

    return (await commandProcess.exited) === 0;
  } catch {
    return false;
  }
};

const main = async (): Promise<void> => {
  if (!process.env.OPENAI_API_KEY) {
    console.error('OPENAI_API_KEY must be set for the live demo runtime');
    process.exitCode = 1;
    return;
  }

  const configuredCodexExecutable = process.env.RELEASE_ASSURANCE_CODEX_EXECUTABLE ?? 'codex';
  const codexInvocation = resolveCommandInvocation(configuredCodexExecutable, ['--version']);
  if (!codexInvocation || !(await verifyCommand(codexInvocation.command))) {
    console.error(`Codex executable was not found or failed: ${configuredCodexExecutable}`);
    process.exitCode = 1;
    return;
  }

  const pythonExecutable = resolvePythonExecutable();
  if (!(await verifyCommand([pythonExecutable, '-c', 'import openai']))) {
    console.error('The Python OpenAI SDK is not installed. Activate the virtual environment and run make setup.');
    process.exitCode = 1;
    return;
  }

  const temporaryDirectory = await mkdtemp(join(tmpdir(), 'release-assurance-live-'));

  console.log('Live demo runtime starting');
  console.log('Open http://127.0.0.1:9000/?director=1 and press Space to start the directed recording');
  console.log('No paid model call occurs until Space is pressed or the live button is clicked manually');

  try {
    process.exitCode = await runDevelopment({
      RELEASE_ASSURANCE_CODEX_EXECUTABLE: codexInvocation.executable,
      RELEASE_ASSURANCE_DB_PATH: join(temporaryDirectory, 'live.sqlite'),
    });
  } finally {
    await rm(temporaryDirectory, { recursive: true, force: true });
  }
};

await main();
