export interface RepoInfo {
  owner: string;
  repo: string;
  type: string;
  localPath: string | null;
  repoUrl: string | null;
}

export default RepoInfo;
