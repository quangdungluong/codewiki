'use client';

import ThemeToggle from '@/components/theme-toggle';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import {
  FaBookOpen,
  FaHome,
  FaExclamationTriangle,
  FaFolder,
  FaGithub,
  FaGitlab,
  FaBitbucket,
  FaDownload,
  FaFileExport,
  FaSync,
} from 'react-icons/fa';
import { useMemo, useState } from 'react';
import { useLanguage } from '@/contexts/LanguageContext';
import { RepoInfo } from '@/types/repoInfo';
import WikiTreeView from '@/components/WikiTreeView';
import Markdown from '@/components/Markdown';

interface WikiSection {
  id: string;
  title: string;
  pages: string[];
  subsections?: string[];
}

interface WikiPage {
  id: string;
  title: string;
  content: string;
  filePaths: string[];
  importance: 'high' | 'medium' | 'low';
  relatedPages: string[];
  parentId?: string;
  isSection?: boolean;
  children?: string[];
}
interface WikiStructure {
  id: string;
  title: string;
  description: string;
  pages: WikiPage[];
  sections: WikiSection[];
  rootSections: string[];
}

// Add CSS styles for wiki with Japanese aesthetic
const wikiStyles = `
  .prose code {
    @apply bg-[var(--background)]/70 px-1.5 py-0.5 rounded font-mono text-xs border border-[var(--border-color)];
  }

  .prose pre {
    @apply bg-[var(--background)]/80 text-[var(--foreground)] rounded-md p-4 overflow-x-auto border border-[var(--border-color)] shadow-sm;
  }

  .prose h1, .prose h2, .prose h3, .prose h4 {
    @apply font-serif text-[var(--foreground)];
  }

  .prose p {
    @apply text-[var(--foreground)] leading-relaxed;
  }

  .prose a {
    @apply text-[var(--accent-primary)] hover:text-[var(--highlight)] transition-colors no-underline border-b border-[var(--border-color)] hover:border-[var(--accent-primary)];
  }

  .prose blockquote {
    @apply border-l-4 border-[var(--accent-primary)]/30 bg-[var(--background)]/30 pl-4 py-1 italic;
  }

  .prose ul, .prose ol {
    @apply text-[var(--foreground)];
  }

  .prose table {
    @apply border-collapse border border-[var(--border-color)];
  }

  .prose th {
    @apply bg-[var(--background)]/70 text-[var(--foreground)] p-2 border border-[var(--border-color)];
  }

  .prose td {
    @apply p-2 border border-[var(--border-color)];
  }
`;

export default function RepoWikiPage() {
  const params = useParams();
  const searchParams = useSearchParams();

  // Extract owner and repo from route params
  const owner = params.owner as string;
  const repo = params.repo as string;

  const repoType = searchParams.get('type') || 'github';
  const localPath = searchParams.get('local_path')
    ? decodeURIComponent(searchParams.get('local_path') || '')
    : undefined;
  const repoUrl = searchParams.get('repo_url')
    ? decodeURIComponent(searchParams.get('repo_url') || '')
    : undefined;
  const language = searchParams.get('language') || 'en';

  const { messages } = useLanguage();

  // Initialize repo info
  const repoInfo = useMemo<RepoInfo>(
    () => ({
      owner,
      repo,
      type: repoType,
      localPath: localPath || null,
      repoUrl: repoUrl || null,
    }),
    [owner, repo, repoType, localPath, repoUrl]
  );

  // Extract wiki structure
  let title = '';
  let description = '';
  let pages: WikiPage[] = [];
  const sections: WikiSection[] = [];
  const rootSections: string[] = [];

  const wikiStructure: WikiStructure = {
    id: 'wiki',
    title,
    description,
    pages,
    sections,
    rootSections,
  };

  const exportWiki = (format: 'markdown' | 'json') => {};
  const handlePageSelect = (pageId: string) => {
    if (currentPageId != pageId) {
      setCurrentPageId(pageId);
    }
  };

  // State variables
  const [isLoading, setIsLoading] = useState(true);
  const [loadingMessage, setLoadingMessage] = useState<string | undefined>(
    messages.loading?.initializing || 'Initializing wiki generation...'
  );
  const [isExporting, setIsExporting] = useState(false);
  const [pagesInProgress, setPagesInProgress] = useState(new Set<string>());
  const [error, setError] = useState<string | null>(null);
  const [effectiveRepoInfo, setEffectiveRepoInfo] = useState(repoInfo); // Track effective repo info with cached data
  const [isComprehensiveView, setIsComprehensiveView] = useState('');
  const [exportError, setExportError] = useState<string | null>(null);
  const [generatedPages, setGeneratedPages] = useState<
    Record<string, WikiPage>
  >({});
  const [currentPageId, setCurrentPageId] = useState<string | undefined>();

  return (
    <div className='h-screen paper-texture p-4 md:p-8 flex flex-col'>
      <style>{wikiStyles}</style>

      <header className='max-w-[90%] xl:max-w-[1400px] mx-auto mb-8 h-fit w-full'>
        <div className='flex flex-col md:flex-row md:items-center md:justify-between gap-4'>
          <div className='flex items-center gap-4'>
            <Link
              href='/'
              className='text-[var(--accent-primary)] hover:text-[var(--highlight)] flex items-center gap-1.5 transition-colors border-b border-[var(--border-color)] hover:border-[var(--accent-primary)] pb-0.5'
            >
              <FaHome /> {messages.repoPage?.home || 'Home'}
            </Link>
          </div>
        </div>
      </header>

      <main className='flex-1 max-w-[90%] xl:max-w-[1400px] mx-auto overflow-y-auto'>
        {isLoading ? (
          <div className='flex flex-col items-center justify-center p-8 bg-[var(--card-bg)] rounded-lg shadow-custom card-japanese'>
            <div className='relative mb-6'>
              <div className='absolute -inset-4 bg-[var(--accent-primary)]/10 rounded-full blur-md animate-pulse'></div>
              <div className='relative flex items-center justify-center'>
                <div className='w-3 h-3 bg-[var(--accent-primary)]/70 rounded-full animate-pulse'></div>
                <div className='w-3 h-3 bg-[var(--accent-primary)]/70 rounded-full animate-pulse delay-75 mx-2'></div>
                <div className='w-3 h-3 bg-[var(--accent-primary)]/70 rounded-full animate-pulse delay-150'></div>
              </div>
            </div>
            <p className='text-[var(--foreground)] text-center mb-3 font-serif'>
              {loadingMessage || messages.common?.loading || 'Loading...'}
              {isExporting &&
                (messages.loading?.preparingDownload ||
                  ' Please wait while we prepare your download...')}
            </p>

            {/* Progress bar for page generation */}
            {wikiStructure && (
              <div className='w-full max-w-md mt-3'>
                <div className='bg-[var(--background)]/50 rounded-full h-2 mb-3 overflow-hidden border border-[var(--border-color)]'>
                  <div
                    className='bg-[var(--accent-primary)] h-2 rounded-full transition-all duration-300 ease-in-out'
                    style={{
                      width: `${Math.max(
                        5,
                        (100 *
                          (wikiStructure.pages.length - pagesInProgress.size)) /
                          wikiStructure.pages.length
                      )}%`,
                    }}
                  />
                </div>
                <p className='text-xs text-[var(--muted)] text-center'>
                  {language === 'ja'
                    ? `${wikiStructure.pages.length}ページ中${
                        wikiStructure.pages.length - pagesInProgress.size
                      }ページ完了`
                    : messages.repoPage?.pagesCompleted
                    ? messages.repoPage.pagesCompleted
                        .replace(
                          '{completed}',
                          (
                            wikiStructure.pages.length - pagesInProgress.size
                          ).toString()
                        )
                        .replace(
                          '{total}',
                          wikiStructure.pages.length.toString()
                        )
                    : `${
                        wikiStructure.pages.length - pagesInProgress.size
                      } of ${wikiStructure.pages.length} pages completed`}
                </p>

                {/* Show list of in-progress pages */}
                {pagesInProgress.size > 0 && (
                  <div className='mt-4 text-xs'>
                    <p className='text-[var(--muted)] mb-2'>
                      {messages.repoPage?.currentlyProcessing ||
                        'Currently processing:'}
                    </p>
                    <ul className='text-[var(--foreground)] space-y-1'>
                      {Array.from(pagesInProgress)
                        .slice(0, 3)
                        .map((pageId) => {
                          const page = wikiStructure.pages.find(
                            (p) => p.id === pageId
                          );
                          return page ? (
                            <li
                              key={pageId}
                              className='truncate border-l-2 border-[var(--accent-primary)]/30 pl-2'
                            >
                              {page.title}
                            </li>
                          ) : null;
                        })}
                      {pagesInProgress.size > 3 && (
                        <li className='text-[var(--muted)]'>
                          {language === 'ja'
                            ? `...他に${pagesInProgress.size - 3}ページ`
                            : messages.repoPage?.andMorePages
                            ? messages.repoPage.andMorePages.replace(
                                '{count}',
                                (pagesInProgress.size - 3).toString()
                              )
                            : `...and ${pagesInProgress.size - 3} more`}
                        </li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : error ? (
          <div className='bg-[var(--highlight)]/5 border border-[var(--highlight)]/30 rounded-lg p-5 mb-4 shadow-sm'>
            <div className='flex items-center text-[var(--highlight)] mb-3'>
              <FaExclamationTriangle className='mr-2' />
              <span className='font-bold font-serif'>
                {messages.repoPage?.errorTitle ||
                  messages.common?.error ||
                  'Error'}
              </span>
            </div>
            <p className='text-[var(--foreground)] text-sm mb-3'>{error}</p>
            <p className='text-[var(--muted)] text-xs'>
              {messages.repoPage?.errorMessageDefault ||
                'Please check that your repository exists and is public. Valid formats are "owner/repo", "https://github.com/owner/repo", "https://gitlab.com/owner/repo", "https://bitbucket.org/owner/repo", or local folder paths like "C:\\path\\to\\folder" or "/path/to/folder".'}
            </p>
            <div className='mt-5'>
              <Link
                href='/'
                className='btn-japanese px-5 py-2 inline-flex items-center gap-1.5'
              >
                <FaHome className='text-sm' />
                {messages.repoPage?.backToHome || 'Back to Home'}
              </Link>
            </div>
          </div>
        ) : wikiStructure ? (
          <div className='h-full overflow-y-auto flex flex-col lg:flex-row gap-4 w-full overflow-hidden bg-[var(--card-bg)] rounded-lg shadow-custom card-japanese'>
            {/* Wiki Navigation */}
            <div className='h-full w-full lg:w-[280px] xl:w-[320px] flex-shrink-0 bg-[var(--background)]/50 rounded-lg rounded-r-none p-5 border-b lg:border-b-0 lg:border-r border-[var(--border-color)] overflow-y-auto'>
              <h3 className='text-lg font-bold text-[var(--foreground)] mb-3 font-serif'>
                {wikiStructure.title}
              </h3>
              <p className='text-[var(--muted)] text-sm mb-5 leading-relaxed'>
                {wikiStructure.description}
              </p>

              {/* Display repository info */}
              <div className='text-xs text-[var(--muted)] mb-5 flex items-center'>
                {effectiveRepoInfo.type === 'local' ? (
                  <div className='flex items-center'>
                    <FaFolder className='mr-2' />
                    <span className='break-all'>
                      {effectiveRepoInfo.localPath}
                    </span>
                  </div>
                ) : (
                  <>
                    {effectiveRepoInfo.type === 'github' ? (
                      <FaGithub className='mr-2' />
                    ) : effectiveRepoInfo.type === 'gitlab' ? (
                      <FaGitlab className='mr-2' />
                    ) : (
                      <FaBitbucket className='mr-2' />
                    )}
                    <a
                      href={effectiveRepoInfo.repoUrl ?? ''}
                      target='_blank'
                      rel='noopener noreferrer'
                      className='hover:text-[var(--accent-primary)] transition-colors border-b border-[var(--border-color)] hover:border-[var(--accent-primary)]'
                    >
                      {effectiveRepoInfo.owner}/{effectiveRepoInfo.repo}
                    </a>
                  </>
                )}
              </div>

              {/* Wiki Type Indicator */}
              <div className='mb-3 flex items-center text-xs text-[var(--muted)]'>
                <span className='mr-2'>Wiki Type:</span>
                <span
                  className={`px-2 py-0.5 rounded-full ${
                    isComprehensiveView
                      ? 'bg-[var(--accent-primary)]/10 text-[var(--accent-primary)] border border-[var(--accent-primary)]/30'
                      : 'bg-[var(--background)] text-[var(--foreground)] border border-[var(--border-color)]'
                  }`}
                >
                  {isComprehensiveView
                    ? messages.form?.comprehensive || 'Comprehensive'
                    : messages.form?.concise || 'Concise'}
                </span>
              </div>

              {/* Refresh Wiki button */}
              <div className='mb-5'>
                <button
                  disabled={isLoading}
                  className='flex items-center w-full text-xs px-3 py-2 bg-[var(--background)] text-[var(--foreground)] rounded-md hover:bg-[var(--background)]/80 disabled:opacity-50 disabled:cursor-not-allowed border border-[var(--border-color)] transition-colors hover:cursor-pointer'
                >
                  <FaSync
                    className={`mr-2 ${isLoading ? 'animate-spin' : ''}`}
                  />
                  {messages.repoPage?.refreshWiki || 'Refresh Wiki'}
                </button>
              </div>

              {/* Export buttons */}
              {Object.keys(generatedPages).length > 0 && (
                <div className='mb-5'>
                  <h4 className='text-sm font-semibold text-[var(--foreground)] mb-3 font-serif'>
                    {messages.repoPage?.exportWiki || 'Export Wiki'}
                  </h4>
                  <div className='flex flex-col gap-2'>
                    <button
                      onClick={() => exportWiki('markdown')}
                      disabled={isExporting}
                      className='btn-japanese flex items-center text-xs px-3 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed'
                    >
                      <FaDownload className='mr-2' />
                      {messages.repoPage?.exportAsMarkdown ||
                        'Export as Markdown'}
                    </button>
                    <button
                      onClick={() => exportWiki('json')}
                      disabled={isExporting}
                      className='flex items-center text-xs px-3 py-2 bg-[var(--background)] text-[var(--foreground)] rounded-md hover:bg-[var(--background)]/80 disabled:opacity-50 disabled:cursor-not-allowed border border-[var(--border-color)] transition-colors'
                    >
                      <FaFileExport className='mr-2' />
                      {messages.repoPage?.exportAsJson || 'Export as JSON'}
                    </button>
                  </div>
                  {exportError && (
                    <div className='mt-2 text-xs text-[var(--highlight)]'>
                      {exportError}
                    </div>
                  )}
                </div>
              )}

              <h4 className='text-md font-semibold text-[var(--foreground)] mb-3 font-serif'>
                {messages.repoPage?.pages || 'Pages'}
              </h4>
              <WikiTreeView
                wikiStructure={wikiStructure}
                currentPageId={currentPageId}
                onPageSelect={handlePageSelect}
                messages={messages.repoPage}
              />
            </div>

            {/* Wiki Content */}
            <div
              id='wiki-content'
              className='w-full flex-grow p-6 lg:p-8 overflow-y-auto'
            >
              {currentPageId && generatedPages[currentPageId] ? (
                <div className='max-w-[900px] xl:max-w-[1000px] mx-auto'>
                  <h3 className='text-xl font-bold text-[var(--foreground)] mb-4 break-words font-serif'>
                    {generatedPages[currentPageId].title}
                  </h3>

                  <div className='prose prose-sm md:prose-base lg:prose-lg max-w-none'>
                    <Markdown content={generatedPages[currentPageId].content} />
                  </div>

                  {generatedPages[currentPageId].relatedPages.length > 0 && (
                    <div className='mt-8 pt-4 border-t border-[var(--border-color)]'>
                      <h4 className='text-sm font-semibold text-[var(--muted)] mb-3'>
                        {messages.repoPage?.relatedPages || 'Related Pages:'}
                      </h4>
                      <div className='flex flex-wrap gap-2'>
                        {generatedPages[currentPageId].relatedPages.map(
                          (relatedId) => {
                            const relatedPage = wikiStructure.pages.find(
                              (p) => p.id === relatedId
                            );
                            return relatedPage ? (
                              <button
                                key={relatedId}
                                className='bg-[var(--accent-primary)]/10 hover:bg-[var(--accent-primary)]/20 text-xs text-[var(--accent-primary)] px-3 py-1.5 rounded-md transition-colors truncate max-w-full border border-[var(--accent-primary)]/20'
                                onClick={() => handlePageSelect(relatedId)}
                              >
                                {relatedPage.title}
                              </button>
                            ) : null;
                          }
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className='flex flex-col items-center justify-center p-8 text-[var(--muted)] h-full'>
                  <div className='relative mb-4'>
                    <div className='absolute -inset-2 bg-[var(--accent-primary)]/5 rounded-full blur-md'></div>
                    <FaBookOpen className='text-4xl relative z-10' />
                  </div>
                  <p className='font-serif'>
                    {messages.repoPage?.selectPagePrompt ||
                      'Select a page from the navigation to view its content'}
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : null}
      </main>

      <footer className='max-w-[90%] xl:max-w-[1400px] mx-auto mt-8 flex flex-col gap-4 w-full'>
        <div className='flex justify-between items-center gap-4 text-center text-[var(--muted)] text-sm h-fit w-full bg-[var(--card-bg)] rounded-lg p-3 shadow-sm border border-[var(--border-color)]'>
          <p className='flex-1 font-serif'>
            {messages.footer?.copyright ||
              'DeepWiki - Generate Wiki from GitHub/Gitlab/Bitbucket repositories'}
          </p>
          <ThemeToggle />
        </div>
      </footer>
    </div>
  );
}
