'use client';

import ThemeToggle from '@/components/theme-toggle';
import { useLanguage } from '@/contexts/LanguageContext';
import { useProcessedProjects } from '@/hooks/useProcessedProjects';
import parseRepoInput from '@/utils/parseRepoInput';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { FaGithub, FaWikipediaW } from 'react-icons/fa';

export default function Home() {
  const router = useRouter();
  const { projects, isLoading: projectsLoading } = useProcessedProjects();
  const { language, setLanguage, messages, supportedLanguages } = useLanguage();
  const [repositoryInput, setRepositoryInput] = useState(
    'https://github.com/AsyncFuncAI/deepwiki-open'
  );
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Create a simple translation function
  const t = (
    key: string,
    params: Record<string, string | number> = {}
  ): string => {
    const keys = key.split('.');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let value: any = messages;

    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        return key;
      }
    }

    if (typeof value === 'string') {
      return Object.entries(params).reduce(
        (acc: string, [paramKey, paramValue]) => {
          return acc.replace(`{${paramKey}}`, String(paramValue));
        },
        value
      );
    }

    return key;
  };

  const handleGenerateWiki = async () => {
    if (isSubmitting) {
      console.log('Already submitting');
      return;
    }
    setIsSubmitting(true);

    // Parse the repository input
    const parsedRepository = parseRepoInput(repositoryInput);
    if (!parsedRepository) {
      setError('Invalid repository path');
      setIsSubmitting(false);
      return;
    }

    const { owner, repo, type, localPath } = parsedRepository;
    const params = new URLSearchParams();
    params.append('type', type === 'local' ? 'local' : 'github');
    if (localPath) {
      params.append('localPath', localPath);
    } else {
      params.append('repoUrl', repositoryInput);
    }
    const queryString = params.toString() ? `?${params.toString()}` : '';

    router.push(`/${owner}/${repo}${queryString}`);
  };

  return (
    <div className='h-screen paper-texture p-4 md:p-8 flex flex-col'>
      <header className='max-w-6xl mx-auto mb-6 h-fit w-full'>
        <div className='flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-[var(--card-bg)] rounded-lg shadow-custom border border-[var(--border-color)] p-4'>
          <div className='flex items-center'>
            <div className='bg-[var(--accent-primary)] p-2 rounded-lg mr-3'>
              <FaWikipediaW className='text-2xl text-white' />
            </div>
            <div className='mr-6'>
              <h1 className='text-xl md:text-2xl font-bold text-[var(--accent-primary)]'>
                {t('common.appName')}
              </h1>
              <div className='flex flex-wrap items-baseline gap-x-2 md:gap-x-3 mt-0.5'>
                <p className='text-xs text-[var(--muted)] whitespace-nowrap'>
                  {t('common.tagline')}
                </p>
                <div className='hidden md:inline-block'>
                  <Link
                    href='/wiki/projects'
                    className='text-xs font-medium text-[var(--accent-primary)] hover:text-[var(--highlight)] hover:underline whitespace-nowrap'
                  >
                    {t('nav.wikiProjects')}
                  </Link>
                </div>
              </div>
            </div>
          </div>

          <form
            onSubmit={handleGenerateWiki}
            className='flex flex-col gap-3 w-full max-w-3xl'
          >
            <div className='flex flex-col sm:flex-row gap-2'>
              <div className='relative flex-1'>
                <input
                  type='text'
                  value={repositoryInput}
                  placeholder='Input repository path'
                  onChange={(e) => setRepositoryInput(e.target.value)}
                  className='input-japanese block w-full pl-10 pr-3 py-2.5 border-[var(--border-color)] rounded-lg bg-transparent text-[var(--foreground)] focus:outline-none focus:border-[var(--accent-primary)]'
                />
                {error && (
                  <div className='text-[var(--highlight)] text-xs mt-1'>
                    {error}
                  </div>
                )}
              </div>
              <button
                type='submit'
                className='btn-japanese px-6 py-2.5 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed'
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Processing...' : 'Generate Wiki'}
              </button>
            </div>
          </form>
        </div>
      </header>

      <main className='flex-1 max-w-6xl mx-auto w-full overflow-y-auto'>
        <div className='min-h-full flex flex-col items-center p-8 pt-10 bg-[var(--card-bg)] rounded-lg shadow-custom card-japanese'>
          {/* Conditionally show processed projects or welcome content */}
          {!projectsLoading && projects.length > 0 ? (
            <div className='w-full'>
              {/* Header section for existing projects */}
              <div className='flex flex-col items-center w-full max-w-2xl mb-8 mx-auto'>
                <div className='flex flex-col sm:flex-row items-center mb-6 gap-4'>
                  <div className='relative'>
                    <div className='absolute -inset-1 bg-[var(--accent-primary)]/20 rounded-full blur-md'></div>
                    <FaWikipediaW className='text-5xl text-[var(--accent-primary)] relative z-10' />
                  </div>
                  <div className='text-center sm:text-left'>
                    <h2 className='text-2xl font-bold text-[var(--foreground)] font-serif mb-1'>
                      {t('projects.existingProjects')}
                    </h2>
                    <p className='text-[var(--accent-primary)] text-sm max-w-md'>
                      {t('projects.browseExisting')}
                    </p>
                  </div>
                </div>
              </div>

              {/* Show processed projects */}
              <ProcessedProjects
                showHeader={false}
                maxItems={6}
                messages={messages}
                className='w-full'
              />
            </div>
          ) : (
            <>
              {/* Header section */}
              <div className='flex flex-col items-center w-full max-w-2xl mb-8'>
                <div className='flex flex-col sm:flex-row items-center mb-6 gap-4'>
                  <div className='relative'>
                    <div className='absolute -inset-1 bg-[var(--accent-primary)]/20 rounded-full blur-md'></div>
                    <FaWikipediaW className='text-5xl text-[var(--accent-primary)] relative z-10' />
                  </div>
                  <div className='text-center sm:text-left'>
                    <h2 className='text-2xl font-bold text-[var(--foreground)] font-serif mb-1'>
                      {t('home.welcome')}
                    </h2>
                    <p className='text-[var(--accent-primary)] text-sm max-w-md'>
                      {t('home.welcomeTagline')}
                    </p>
                  </div>
                </div>

                <p className='text-[var(--foreground)] text-center mb-8 text-lg leading-relaxed'>
                  {t('home.description')}
                </p>
              </div>

              {/* Quick Start section - redesigned for better spacing */}
              <div className='w-full max-w-2xl mb-10 bg-[var(--accent-primary)]/5 border border-[var(--accent-primary)]/20 rounded-lg p-5'>
                <h3 className='text-sm font-semibold text-[var(--accent-primary)] mb-3 flex items-center'>
                  <svg
                    xmlns='http://www.w3.org/2000/svg'
                    className='h-4 w-4 mr-2'
                    fill='none'
                    viewBox='0 0 24 24'
                    stroke='currentColor'
                  >
                    <path
                      strokeLinecap='round'
                      strokeLinejoin='round'
                      strokeWidth={2}
                      d='M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
                    />
                  </svg>
                  {t('home.quickStart')}
                </h3>
                <p className='text-sm text-[var(--foreground)] mb-3'>
                  {t('home.enterRepoUrl')}
                </p>
                <div className='grid grid-cols-1 gap-3 text-xs text-[var(--muted)]'>
                  <div className='bg-[var(--background)]/70 p-3 rounded border border-[var(--border-color)] font-mono overflow-x-hidden whitespace-nowrap'>
                    https://github.com/AsyncFuncAI/deepwiki-open
                  </div>
                  <div className='bg-[var(--background)]/70 p-3 rounded border border-[var(--border-color)] font-mono overflow-x-hidden whitespace-nowrap'>
                    https://gitlab.com/gitlab-org/gitlab
                  </div>
                  <div className='bg-[var(--background)]/70 p-3 rounded border border-[var(--border-color)] font-mono overflow-x-hidden whitespace-nowrap'>
                    AsyncFuncAI/deepwiki-open
                  </div>
                  <div className='bg-[var(--background)]/70 p-3 rounded border border-[var(--border-color)] font-mono overflow-x-hidden whitespace-nowrap'>
                    https://bitbucket.org/atlassian/atlaskit
                  </div>
                </div>
              </div>

              {/* Visualization section - improved for better visibility */}
              <div className='w-full max-w-2xl mb-8 bg-[var(--background)]/70 rounded-lg p-6 border border-[var(--border-color)]'>
                <div className='flex flex-col sm:flex-row items-start sm:items-center gap-2 mb-4'>
                  <svg
                    xmlns='http://www.w3.org/2000/svg'
                    className='h-5 w-5 text-[var(--accent-primary)] flex-shrink-0 mt-0.5 sm:mt-0'
                    fill='none'
                    viewBox='0 0 24 24'
                    stroke='currentColor'
                  >
                    <path
                      strokeLinecap='round'
                      strokeLinejoin='round'
                      strokeWidth={2}
                      d='M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z'
                    />
                  </svg>
                  <h3 className='text-base font-semibold text-[var(--foreground)] font-serif'>
                    {t('home.advancedVisualization')}
                  </h3>
                </div>
                <p className='text-sm text-[var(--foreground)] mb-5 leading-relaxed'>
                  {t('home.diagramDescription')}
                </p>

                {/* Diagrams with improved layout */}
                <div className='grid grid-cols-1 gap-6'>
                  <div className='bg-[var(--card-bg)] p-4 rounded-lg border border-[var(--border-color)] shadow-custom'>
                    <h4 className='text-sm font-medium text-[var(--foreground)] mb-3 font-serif'>
                      {t('home.flowDiagram')}
                    </h4>
                    {/* <Mermaid chart={DEMO_FLOW_CHART} /> */}
                  </div>

                  <div className='bg-[var(--card-bg)] p-4 rounded-lg border border-[var(--border-color)] shadow-custom'>
                    <h4 className='text-sm font-medium text-[var(--foreground)] mb-3 font-serif'>
                      {t('home.sequenceDiagram')}
                    </h4>
                    {/* <Mermaid chart={DEMO_SEQUENCE_CHART} /> */}
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </main>

      <footer className='max-w-6xl mx-auto mt-8 flex flex-col gap-4 w-full'>
        <div className='flex flex-col sm:flex-row justify-between items-center gap-4 bg-[var(--card-bg)] rounded-lg p-4 border border-[var(--border-color)] shadow-custom'>
          <p className='text-[var(--muted)] text-sm font-serif'>
            {t('footer.copyright')}
          </p>

          <div className='flex items-center gap-6'>
            <div className='flex items-center space-x-5'>
              <a
                href='https://github.com/AsyncFuncAI/deepwiki-open'
                target='_blank'
                rel='noopener noreferrer'
                className='text-[var(--muted)] hover:text-[var(--accent-primary)] transition-colors'
              >
                <FaGithub className='text-xl' />
              </a>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </footer>
    </div>
  );
}
