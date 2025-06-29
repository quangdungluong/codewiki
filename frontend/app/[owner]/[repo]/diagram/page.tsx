'use client';
import { useDiagram } from '@/hooks/useDiagram';
import { useParams } from 'next/navigation';
import { useState } from 'react';
import MermaidChart from '@/components/Mermaid';
import DiagramLoading from '@/components/DiagramLoading';
import { FaBook, FaProjectDiagram } from 'react-icons/fa';
import Link from 'next/link';
import { FaHome } from 'react-icons/fa';
import { useLanguage } from '@/contexts/LanguageContext';
import ThemeToggle from '@/components/theme-toggle';

export default function DiagramPage() {
  const [zoomingEnabled, setZoomingEnabled] = useState(false);
  const params = useParams<{ owner: string; repo: string }>();
  const { messages } = useLanguage();

  const { diagram, loading, error, state } = useDiagram(
    params.owner,
    params.repo
  );
  return (
    <div className='h-screen paper-texture p-4 md:p-8 flex flex-col'>
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
          <div className='flex items-center gap-4'>
            <Link href={`/${params.owner}/${params.repo}`}>
              <button className='btn-japanese flex items-center text-sm px-3 py-2 rounded-md disabled:opacity-50 disabled:cursor-not-allowed'>
                <FaBook className='mr-2' />
                {'Wiki'}
              </button>
            </Link>
          </div>
        </div>
      </header>

      <div className='flex flex-col items-center p-4'>
        <div className='mt-8 flex w-full flex-col items-center gap-8'>
          {loading ? (
            <DiagramLoading
              status={state.status}
              explanation={state.explanation}
              mapping={state.mapping}
              diagram={state.diagram}
            />
          ) : error || state.error ? (
            <div className='mt-12 text-center'>
              <p className='max-w-4xl text-lg font-medium text-purple-600'>
                {error || state.error}
              </p>
            </div>
          ) : (
            <div className='flex w-full justify-center px-4'>
              <MermaidChart chart={diagram} zoomingEnabled={zoomingEnabled} />
            </div>
          )}
        </div>
      </div>

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
