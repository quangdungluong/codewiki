import { extractUrlPath } from '@/utils/urlDecoder';

export default function parseRepoInput(input: string): {
  owner: string;
  repo: string;
  type: string;
  fullPath?: string;
  localPath?: string;
} | null {
  input = input.trim();

  let owner = '',
    repo = '',
    type = 'github',
    fullPath;
  let localPath: string | undefined;

  const windowsPathRegex =
    /^[a-zA-Z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*$/;
  const customGitRegex =
    /^(?:https?:\/\/)?([^\/]+)\/(.+?)\/([^\/]+)(?:\.git)?\/?$/;

  if (windowsPathRegex.test(input)) {
    type = 'local';
    localPath = input;
    repo = input.split('\\').pop() || 'local-repo';
    owner = 'local';
  } else if (input.startsWith('/')) {
    type = 'local';
    localPath = input;
    repo = input.split('/').filter(Boolean).pop() || 'local-repo';
    owner = 'local';
  } else if (customGitRegex.test(input)) {
    type = 'web';
    fullPath = extractUrlPath(input)?.replace(/\.git$/, '');
    const parts = fullPath?.split('/') ?? [];
    if (parts.length >= 2) {
      repo = parts[parts.length - 1] || '';
      owner = parts[parts.length - 2] || '';
    }
  } else {
    console.error('Invalid repository input:', input);
    return null;
  }

  if (!owner || !repo) {
    console.error('Owner or repo not found:', owner, repo);
    return null;
  }

  owner = owner.trim();
  repo = repo.trim();

  // Remove .git
  if (repo.endsWith('.git')) {
    repo = repo.slice(0, -4);
  }

  return { owner, repo, type, fullPath, localPath };
}
