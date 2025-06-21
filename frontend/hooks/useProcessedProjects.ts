import { useState, useEffect } from "react";

interface ProcessedProject {
    id: string;
    owner: string;
    repo: string;
    name: string;
    repoType: string;
    submittedAt: string;

}

export function useProcessedProjects() {
    const [projects, setProjects] = useState<ProcessedProject[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchProjects = async () => {
            setIsLoading(true);
            setError(null);

            try {
                const response = await fetch('/api/wiki/projects');
                if (!response.ok) {
                    throw new Error(`Failed to fetch projects: ${response.statusText}`);
                }
                const data = await response.json();
                if (data.error) {
                    throw new Error(data.error);
                }
                setProjects(data as ProcessedProject[]);
            } catch (err) {
                console.error('Error fetching projects:', err);
                const message = err instanceof Error ? err.message : 'An unknown error occurred';
                setError(message);
                setProjects([]);
            } finally {
                setIsLoading(false);
            }
        };
        fetchProjects();
    }, []);

    return { projects, isLoading, error };
}
