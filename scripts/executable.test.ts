import { describe, expect, test } from 'bun:test';

import { commandForExecutable, resolveCommandInvocation } from './executable';

describe('commandForExecutable', () => {
  test('executes native binaries directly', () => {
    expect(commandForExecutable('/usr/local/bin/codex', ['--version'], 'darwin')).toEqual(['/usr/local/bin/codex', '--version']);
    expect(commandForExecutable('C:\\Tools\\codex.exe', ['--version'], 'win32')).toEqual(['C:\\Tools\\codex.exe', '--version']);
  });

  test('uses the Windows command processor for npm shims', () => {
    expect(commandForExecutable('C:\\Program Files\\nodejs\\codex.cmd', ['--version'], 'win32', 'C:\\Windows\\System32\\cmd.exe')).toEqual([
      'C:\\Windows\\System32\\cmd.exe',
      '/d',
      '/s',
      '/c',
      '""C:\\Program Files\\nodejs\\codex.cmd" "--version""',
    ]);
  });
});

describe('resolveCommandInvocation', () => {
  test('falls back to the npm command shim before constructing the invocation', () => {
    const invocation = resolveCommandInvocation('codex', ['--version'], {
      comspec: 'cmd.exe',
      platform: 'win32',
      which: (candidate) => (candidate === 'codex.cmd' ? 'C:\\Users\\builder\\AppData\\Roaming\\npm\\codex.cmd' : null),
    });

    expect(invocation).toEqual({
      command: ['cmd.exe', '/d', '/s', '/c', '""C:\\Users\\builder\\AppData\\Roaming\\npm\\codex.cmd" "--version""'],
      executable: 'C:\\Users\\builder\\AppData\\Roaming\\npm\\codex.cmd',
    });
  });

  test('returns null when the command is unavailable', () => {
    expect(resolveCommandInvocation('codex', ['--version'], { which: () => null })).toBeNull();
  });
});
