import { SavedResearch } from './supabase';

const CACHE_KEY = 'quorum_local_research_history';

/**
 * Retrieves cached research results from localStorage
 */
export function getLocalResearchCache(): SavedResearch[] {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    console.warn('Failed to read research cache from localStorage:', e);
    return [];
  }
}

/**
 * Saves a completed research dossier to local cache
 */
export function saveToLocalResearchCache(item: SavedResearch): void {
  try {
    if (!item || !item.topic || !item.report_markdown) return;
    const current = getLocalResearchCache();
    const normalizedTopic = item.topic.toLowerCase().trim();

    // Remove any existing duplicate by ID or topic
    const filtered = current.filter(
      (c) =>
        (c.id && item.id && c.id === item.id) ||
        c.topic.toLowerCase().trim() !== normalizedTopic
    );

    const updated = [item, ...filtered].slice(0, 50);
    localStorage.setItem(CACHE_KEY, JSON.stringify(updated));
  } catch (e) {
    console.warn('Failed to save to local research cache:', e);
  }
}

/**
 * Finds a cached research dossier by topic string
 */
export function findCachedResearch(topic: string): SavedResearch | undefined {
  if (!topic) return undefined;
  const current = getLocalResearchCache();
  const normalized = topic.toLowerCase().trim();
  return current.find((c) => c.topic.toLowerCase().trim() === normalized);
}

/**
 * Merges Supabase research records into localStorage cache
 */
export function syncSupabaseIntoLocalCache(supabaseItems: SavedResearch[]): void {
  try {
    if (!supabaseItems || supabaseItems.length === 0) return;
    const current = getLocalResearchCache();
    const map = new Map<string, SavedResearch>();

    // 1. Load local items into map
    current.forEach((item) => {
      if (item.topic) {
        map.set(item.topic.toLowerCase().trim(), item);
      }
    });

    // 2. Overwrite / insert Supabase cloud items (authoritative)
    supabaseItems.forEach((item) => {
      if (item.topic && item.report_markdown) {
        map.set(item.topic.toLowerCase().trim(), item);
      }
    });

    const merged = Array.from(map.values()).sort((a, b) => {
      const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return timeB - timeA;
    });

    localStorage.setItem(CACHE_KEY, JSON.stringify(merged.slice(0, 50)));
  } catch (e) {
    console.warn('Failed to sync Supabase items into cache:', e);
  }
}
