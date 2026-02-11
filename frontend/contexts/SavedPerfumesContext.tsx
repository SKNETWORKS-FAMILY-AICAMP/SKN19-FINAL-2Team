"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

const BACKEND_URL = "/api";

type SavedPerfumesContextType = {
  savedPerfumeIds: Set<number>;
  addSavedPerfume: (id: number) => void;
  isSaved: (id: number) => boolean;
  loading: boolean;
};

const SavedPerfumesContext = createContext<SavedPerfumesContextType | null>(null);

export function SavedPerfumesProvider({ 
  children, 
  memberId 
}: { 
  children: ReactNode; 
  memberId: number | null;
}) {
  const [savedPerfumeIds, setSavedPerfumeIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!memberId || memberId === 0) {
      setLoading(false);
      return;
    }

    const fetchSavedPerfumes = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/users/${memberId}/perfumes`);
        if (!response.ok) {
          console.error('Failed to fetch saved perfumes:', response.statusText);
          return;
        }

        const data = await response.json();
        const ids = new Set<number>(
          data
            .map((p: any) => Number(p.perfume_id))
            .filter((n: number) => Number.isFinite(n))
        );
        setSavedPerfumeIds(ids);
      } catch (error) {
        console.error('Error fetching saved perfumes:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSavedPerfumes();
  }, [memberId]);

  const addSavedPerfume = (id: number) => {
    setSavedPerfumeIds(prev => new Set(prev).add(id));
  };

  const isSaved = (id: number) => savedPerfumeIds.has(id);

  return (
    <SavedPerfumesContext.Provider value={{ savedPerfumeIds, addSavedPerfume, isSaved, loading }}>
      {children}
    </SavedPerfumesContext.Provider>
  );
}

export const useSavedPerfumes = () => {
  const context = useContext(SavedPerfumesContext);
  if (!context) {
    throw new Error('useSavedPerfumes must be used within SavedPerfumesProvider');
  }
  return context;
};
