/**
 * Quorum FastAPI Backend Client
 * Connects the frontend to the live Python multi-agent execution pipeline.
 */

import { supabase } from './supabase';

export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  try {
    const { data } = await supabase.auth.getSession();
    if (data?.session?.access_token) {
      headers['Authorization'] = `Bearer ${data.session.access_token}`;
    }
  } catch {}
  return headers;
}

export interface AgentLogMessage {
  agent: 'Planner' | 'Researcher' | 'Critic' | 'Writer' | 'Supervisor' | 'System';
  status: string;
  is_rejection?: boolean;
  is_approval?: boolean;
}

export interface ResearchFindingItem {
  question: string;
  answer: string;
  sources?: string[];
  critic_attempts?: number;
  critic_scores?: {
    approved?: boolean;
    grounding_score?: number;
    completeness_score?: number;
    recency_score?: number;
    feedback?: string;
  };
}

export interface DonePayload {
  report: string;
  metrics: Record<string, any>;
  findings: ResearchFindingItem[];
}

export interface StreamCallbacks {
  onLog: (data: AgentLogMessage) => void;
  onChunk?: (chunk: string) => void;
  onDone: (data: DonePayload) => void;
  onError: (errorMsg: string) => void;
}

/**
 * Check if the FastAPI backend is running and reachable.
 */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(3000),
    });
    if (!res.ok) return false;
    const data = await res.json();
    return data?.status === 'ok';
  } catch {
    return false;
  }
}

/**
 * Step 1: Call Planner Agent to break down a topic into research subquestions.
 */
export async function generateResearchPlan(
  topic: string,
  base64Image?: string | null
): Promise<string[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/plan`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      topic,
      base64_image: base64Image || null,
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Failed to generate research plan: ${errText}`);
  }

  const data = await res.json();
  return data.subquestions || [];
}

/**
 * Step 2: Stream multi-agent execution live via SSE.
 * Uses native browser EventSource for robust, resilient streaming with optional auth token.
 */
export function streamResearchExecution(
  topic: string,
  callbacks: StreamCallbacks
): () => void {
  let eventSource: EventSource | null = null;
  let isClosed = false;

  (async () => {
    try {
      let token = '';
      try {
        const { data } = await supabase.auth.getSession();
        token = data?.session?.access_token || '';
      } catch {}

      if (isClosed) return;

      const tokenParam = token ? `&token=${encodeURIComponent(token)}` : '';
      const url = `${API_BASE}/api/stream?topic=${encodeURIComponent(topic)}${tokenParam}`;
      eventSource = new EventSource(url);

      eventSource.addEventListener('report_chunk', (event: MessageEvent) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.chunk !== undefined && callbacks.onChunk) {
            callbacks.onChunk(parsed.chunk);
          }
        } catch (err) {
          console.warn('Failed to parse SSE report_chunk:', err);
        }
      });

      eventSource.addEventListener('agent_log', (event: MessageEvent) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed.type === 'done') {
            callbacks.onDone({
              report: parsed.report,
              metrics: parsed.metrics || {},
              findings: parsed.findings || [],
            });
            eventSource?.close();
          } else {
            callbacks.onLog(parsed);
          }
        } catch (err) {
          console.warn('Failed to parse SSE agent_log:', err);
        }
      });

      eventSource.addEventListener('error', (event: any) => {
        try {
          if (event.data) {
            const parsed = JSON.parse(event.data);
            callbacks.onError(parsed.error || 'Swarm execution error');
          } else {
            callbacks.onError('Connection to Quorum multi-agent server interrupted.');
          }
        } catch {
          callbacks.onError('Connection interrupted');
        }
        eventSource?.close();
      });
    } catch (err: any) {
      callbacks.onError(err.message || 'Failed to initialize SSE stream');
    }
  })();

  return () => {
    isClosed = true;
    eventSource?.close();
  };
}

/**
 * Export research report as PDF via backend xhtml2pdf service.
 */
export async function exportReportPdf(topic: string, markdownReport: string): Promise<Blob> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/export_pdf`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      topic,
      markdown_report: markdownReport,
    }),
  });

  if (!res.ok) {
    throw new Error('Failed to generate PDF report from backend');
  }

  return await res.blob();
}

/**
 * Step 2 (HITL): Stream multi-agent execution with user-edited sub-questions via POST SSE.
 * Uses fetch + ReadableStream since EventSource only supports GET.
 */
export function streamResearchWithPlan(
  topic: string,
  customSubquestions: string[],
  callbacks: StreamCallbacks
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const headers = await getAuthHeaders();
      const res = await fetch(`${API_BASE}/api/execute`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ topic, custom_subquestions: customSubquestions }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) {
        callbacks.onError(`Backend returned ${res.status}`);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      let hasCompleted = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmedLine = line.trim();
          if (trimmedLine.startsWith('data:')) {
            const jsonStr = trimmedLine.slice(5).trim();
            if (!jsonStr) continue;
            try {
              const parsed = JSON.parse(jsonStr);
              if (parsed.type === 'done') {
                hasCompleted = true;
                callbacks.onDone({
                  report: parsed.report,
                  metrics: parsed.metrics || {},
                  findings: parsed.findings || [],
                });
                return;
              } else if (parsed.chunk !== undefined) {
                callbacks.onChunk?.(parsed.chunk);
              } else if (parsed.error) {
                hasCompleted = true;
                callbacks.onError(parsed.error);
                return;
              } else {
                callbacks.onLog(parsed);
              }
            } catch {}
          }
        }
      }

      // Check remaining buffer when reader completes
      if (buffer.trim()) {
        const trimmedLine = buffer.trim();
        if (trimmedLine.startsWith('data:')) {
          const jsonStr = trimmedLine.slice(5).trim();
          if (jsonStr) {
            try {
              const parsed = JSON.parse(jsonStr);
              if (parsed.type === 'done') {
                hasCompleted = true;
                callbacks.onDone({
                  report: parsed.report,
                  metrics: parsed.metrics || {},
                  findings: parsed.findings || [],
                });
                return;
              } else if (parsed.chunk !== undefined) {
                callbacks.onChunk?.(parsed.chunk);
              } else if (parsed.error) {
                hasCompleted = true;
                callbacks.onError(parsed.error);
                return;
              } else {
                callbacks.onLog(parsed);
              }
            } catch {}
          }
        }
      }

      if (!hasCompleted && !controller.signal.aborted) {
        callbacks.onError('Research stream completed without final report');
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        callbacks.onError(err.message || 'Stream connection failed');
      }
    }
  })();

  return () => controller.abort();
}

/**
 * Fetch authenticated user's past research history from backend SQLite store.
 */
export async function fetchBackendHistory(): Promise<any[]> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/history`, {
      method: 'GET',
      headers,
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.history || [];
  } catch {
    return [];
  }
}
