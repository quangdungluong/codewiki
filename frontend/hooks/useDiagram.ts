import { useCallback, useEffect, useState } from 'react';

interface StreamState {
  status:
    | 'idle'
    | 'started'
    | 'explanation_sent'
    | 'explanation'
    | 'explanation_chunk'
    | 'mapping_sent'
    | 'mapping'
    | 'mapping_chunk'
    | 'diagram_sent'
    | 'diagram'
    | 'diagram_chunk'
    | 'complete'
    | 'error';
  message?: string;
  explanation?: string;
  mapping?: string;
  diagram?: string;
  error?: string;
}

interface DiagramRequest {
  owner: string;
  repo: string;
  githubPat?: string;
}

interface StreamResponse {
  status: StreamState['status'];
  message?: string;
  chunk?: string;
  explanation?: string;
  mapping?: string;
  diagram?: string;
  error?: string;
}

export function useDiagram(owner: string, repo: string) {
  const [diagram, setDiagram] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [state, setState] = useState<StreamState>({ status: 'idle' });

  const generateDiagram = useCallback(
    async (githubPat?: string) => {
      setState({
        status: 'started',
        message: 'Generating diagram...',
      });
      try {
        const requestBody: DiagramRequest = {
          owner,
          repo,
          githubPat,
        };

        const baseUrl = process.env.SERVER_BASE_URL || 'http://localhost:8001';
        const response = await fetch(`${baseUrl}/api/diagram/generate`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
          throw new Error('Failed to generate diagram');
        }
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('Failed to get reader');
        }

        let explanation = '';
        let mapping = '';
        let diagram = '';

        const processStream = async () => {
          try {
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;

              const chunk = new TextDecoder().decode(value);
              const lines = chunk.split('\n');
              for (const line of lines) {
                if (line.startsWith('data:')) {
                  try {
                    const data = JSON.parse(line.slice(5)) as StreamResponse;
                    if (data.error) {
                      setState({
                        status: 'error',
                        error: data.error,
                      });
                      setLoading(false);
                      return;
                    }
                    console.log(data);
                    switch (data.status) {
                      case 'started':
                        setState((prev) => ({
                          ...prev,
                          status: 'started',
                          message: data.message,
                        }));
                        break;
                      case 'explanation_sent':
                        setState((prev) => ({
                          ...prev,
                          status: 'explanation_sent',
                          message: data.message,
                        }));
                        break;
                      case 'explanation':
                        setState((prev) => ({
                          ...prev,
                          status: 'explanation',
                          message: data.message,
                        }));
                        break;
                      case 'explanation_chunk':
                        if (data.chunk) {
                          explanation += data.chunk;
                          setState((prev) => ({ ...prev, explanation }));
                        }
                        break;
                      case 'mapping_sent':
                        setState((prev) => ({
                          ...prev,
                          status: 'mapping_sent',
                          message: data.message,
                        }));
                        break;
                      case 'mapping':
                        setState((prev) => ({
                          ...prev,
                          status: 'mapping',
                          message: data.message,
                        }));
                        break;
                      case 'mapping_chunk':
                        if (data.chunk) {
                          mapping += data.chunk;
                          setState((prev) => ({ ...prev, mapping }));
                        }
                        break;
                      case 'diagram_sent':
                        setState((prev) => ({
                          ...prev,
                          status: 'diagram_sent',
                          message: data.message,
                        }));
                        break;
                      case 'diagram':
                        setState((prev) => ({
                          ...prev,
                          status: 'diagram',
                          message: data.message,
                        }));
                        break;
                      case 'diagram_chunk':
                        if (data.chunk) {
                          diagram += data.chunk;
                          setState((prev) => ({ ...prev, diagram }));
                        }
                        break;
                      case 'complete':
                        setState({
                          status: 'complete',
                          explanation: data.explanation,
                          diagram: data.diagram,
                        });
                        break;
                      case 'error':
                        setState({ status: 'error', error: data.error });
                        break;
                    }
                  } catch (e) {
                    console.error('Error parsing SSE message:', e);
                  }
                }
              }
            }
          } finally {
            reader.releaseLock();
          }
        };

        await processStream();
      } catch (error) {
        setState({
          status: 'error',
          error:
            error instanceof Error
              ? error.message
              : 'An unknown error occurred',
        });
        setLoading(false);
      }
    },
    [owner, repo]
  );

  useEffect(() => {
    const cacheDiagram = async () => {
      if (state.status === 'complete' && state.diagram) {
        setDiagram(state.diagram);
        const dataToCache = {
          owner: owner,
          repo: repo,
          diagram: state.diagram,
        };
        const response = await fetch(`/api/diagram/cached`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(dataToCache),
        });

        if (response.ok) {
          console.log('Diagram data successfully saved to server cache');
        } else {
          console.error(
            'Error saving diagram data to server cache:',
            response.status,
            await response.text()
          );
        }
      } else if (state.status === 'error') {
        setLoading(false);
      }
    };
    void cacheDiagram();
  }, [state.status, state.diagram, owner, repo]);

  const getDiagram = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const params = new URLSearchParams({
        owner: owner,
        repo: repo,
      });
      const response = await fetch(`/api/diagram/cached?${params.toString()}`);
      if (response.ok) {
        const diagramCached = await response.json();
        if (diagramCached && diagramCached.diagram) {
          setDiagram(diagramCached.diagram);
          return;
        }
      }
      await generateDiagram();
    } catch (error) {
      console.error('Error generating diagram:', error);
      setError('An error occurred while generating the diagram');
    } finally {
      setLoading(false);
    }
  }, [generateDiagram, owner, repo]);

  useEffect(() => {
    void getDiagram();
  }, [getDiagram]);

  return {
    diagram,
    error,
    loading,
    state,
  };
}
