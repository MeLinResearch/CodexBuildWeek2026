import { extname } from 'node:path';

interface ICommandInvocation {
  command: string[];
  executable: string;
}

interface IResolveCommandOptions {
  comspec?: string;
  platform?: NodeJS.Platform;
  which?: (command: string) => string | null;
}

const WINDOWS_COMMAND_SHIM_EXTENSIONS = new Set(['.bat', '.cmd']);

const quoteWindowsCommandArgument = (value: string): string => {
  return `"${value.replaceAll('%', '%%').replaceAll('"', '""')}"`;
};

const commandForExecutable = (
  executable: string,
  args: string[],
  platform: NodeJS.Platform = process.platform,
  comspec = process.env.ComSpec ?? process.env.COMSPEC ?? 'cmd.exe',
): string[] => {
  const extension = extname(executable).toLowerCase();

  if (platform === 'win32' && WINDOWS_COMMAND_SHIM_EXTENSIONS.has(extension)) {
    const commandLine = `"${[executable, ...args].map(quoteWindowsCommandArgument).join(' ')}"`;
    return [comspec, '/d', '/s', '/c', commandLine];
  }

  return [executable, ...args];
};

const resolveCommandInvocation = (command: string, args: string[], options: IResolveCommandOptions = {}): ICommandInvocation | null => {
  const platform = options.platform ?? process.platform;
  const which = options.which ?? Bun.which;
  const candidates = platform === 'win32' && !extname(command) ? [command, `${command}.cmd`] : [command];
  const executable = candidates.map((candidate) => which(candidate)).find((candidate) => candidate !== null);

  if (!executable) {
    return null;
  }

  return {
    command: commandForExecutable(executable, args, platform, options.comspec),
    executable,
  };
};

export type { ICommandInvocation, IResolveCommandOptions };
export { commandForExecutable, resolveCommandInvocation };
