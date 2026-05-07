import { useState, useEffect } from 'react';
import api from '../api/axios';

export interface VocabOption {
  value: string;
  label: string;
}

export interface VocabSource {
  name: string;
  url: string;
}

interface CacheEntry {
  options: VocabOption[];
  source: VocabSource | null;
}

// Module-level cache so the same vocabulary is never fetched twice across components.
const cache = new Map<string, CacheEntry>();

/**
 * Fetch a controlled vocabulary from GET /api/vocabularies/{modelName}/.
 *
 * @param modelName  The model name slug, e.g. 'ethnicity', 'toxicity-grade'.
 * @param valueField 'title' — use the display title as the option value (backward-compatible
 *                             for text fields that already store the title string in the DB).
 *                   'code'  — use the code as the option value (for integer/coded fields;
 *                             integer codes are returned as strings so existing parseInt
 *                             handlers in onChange work unchanged).
 */
export const useVocabulary = (
  modelName: string,
  valueField: 'code' | 'title' = 'title',
): { options: VocabOption[]; loading: boolean; source: VocabSource | null } => {
  const cacheKey = `${modelName}:${valueField}`;
  const cached = cache.get(cacheKey);
  const [options, setOptions] = useState<VocabOption[]>(cached?.options ?? []);
  const [source, setSource] = useState<VocabSource | null>(cached?.source ?? null);
  const [loading, setLoading] = useState(!cache.has(cacheKey));

  useEffect(() => {
    if (cache.has(cacheKey)) return;

    let cancelled = false;
    setLoading(true);

    api
      .get(`/vocabularies/${modelName}/`)
      .then((res) => {
        if (cancelled) return;
        const data: { code: string | number; title: string; source_name?: string; source_url?: string }[] = res.data;
        const opts: VocabOption[] = data.map((item) => ({
          value: valueField === 'code' ? String(item.code) : item.title,
          label: item.title,
        }));
        const first = data[0];
        const src: VocabSource | null =
          first?.source_name && first?.source_url
            ? { name: first.source_name, url: first.source_url }
            : null;
        cache.set(cacheKey, { options: opts, source: src });
        setOptions(opts);
        setSource(src);
      })
      .catch((err) => {
        console.error(`useVocabulary: failed to fetch "${modelName}":`, err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [cacheKey, modelName, valueField]);

  return { options, loading, source };
};
