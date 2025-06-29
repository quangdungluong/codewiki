'use client';
import { useDiagram } from '@/hooks/useDiagram';
import { useParams } from 'next/navigation';
import { useState } from 'react';
import MermaidChart from '@/components/Mermaid';
import DiagramLoading from '@/components/DiagramLoading';

export default function DiagramPage() {
  const [zoomingEnabled, setZoomingEnabled] = useState(false);
  const params = useParams<{ owner: string; repo: string }>();

  const { diagram, loading, error, state } = useDiagram(
    params.owner,
    params.repo
  );
  return (
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
  );
}
