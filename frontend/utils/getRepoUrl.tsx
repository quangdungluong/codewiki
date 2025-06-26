import RepoInfo from '@/types/repoInfo';

export default function getRepoUrl(repoInfo: RepoInfo): string {
  if (repoInfo.type === 'local' && repoInfo.localPath) {
    return repoInfo.localPath;
  } else {
    if (repoInfo.repoUrl) {
      return repoInfo.repoUrl;
    }
    if (repoInfo.owner && repoInfo.repo) {
      return `https://github.com/${repoInfo.owner}/${repoInfo.repo}`;
    }
  }
  return '';
}
