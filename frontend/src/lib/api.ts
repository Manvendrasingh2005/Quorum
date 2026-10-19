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
  base64Image?: string | null,
  depth: string = 'standard'
): Promise<string[]> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/plan`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      topic,
      base64_image: base64Image || null,
      depth,
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
 * Create an asynchronous background research job.
 */
export async function createResearchJob(
  topic: string,
  customSubquestions?: string[],
  depth: string = 'standard'
): Promise<{ job_id: string; status: string; topic: string; depth?: string }> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/jobs`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      topic,
      custom_subquestions: customSubquestions || null,
      depth,
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Failed to create research job: ${errText}`);
  }

  return await res.json();
}

/**
 * Poll or inspect the status and results of a research job.
 */
export async function getJobStatus(jobId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/jobs/${encodeURIComponent(jobId)}`, {
    method: 'GET',
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch status for job ${jobId}`);
  }
  return await res.json();
}

/**
 * Step 2: Stream multi-agent execution live via SSE with automatic reconnection and replay.
 */
export function streamResearchExecution(
  topic: string,
  callbacks: StreamCallbacks,
  depth: string = 'standard'
): () => void {
  let isClosed = false;
  let activeEventSource: EventSource | null = null;
  let lastEventId = 0;
  let retryCount = 0;
  const maxRetries = 5;

  (async () => {
    try {
      // Step 1: Create asynchronous job to obtain stable job_id
      const jobData = await createResearchJob(topic, undefined, depth);
      if (isClosed) return;
      const jobId = jobData.job_id;

      // Step 2: Connect with automatic reconnect and event replayability
      const connectStream = async () => {
        if (isClosed) return;

        let token = '';
        try {
          const { data } = await supabase.auth.getSession();
          token = data?.session?.access_token || '';
        } catch {}

        const tokenParam = token ? `&token=${encodeURIComponent(token)}` : '';
        const url = `${API_BASE}/api/jobs/${encodeURIComponent(jobId)}/stream?last_event_id=${lastEventId}${tokenParam}`;
        activeEventSource = new EventSource(url);

        activeEventSource.addEventListener('report_chunk', (event: MessageEvent) => {
          if (event.lastEventId) {
            const parsedId = parseInt(event.lastEventId, 10);
            if (!isNaN(parsedId)) lastEventId = parsedId;
          }
          try {
            const parsed = JSON.parse(event.data);
            if (parsed.chunk !== undefined && callbacks.onChunk) {
              callbacks.onChunk(parsed.chunk);
            }
          } catch (err) {
            console.warn('Failed to parse SSE report_chunk:', err);
          }
        });

        activeEventSource.addEventListener('agent_log', (event: MessageEvent) => {
          if (event.lastEventId) {
            const parsedId = parseInt(event.lastEventId, 10);
            if (!isNaN(parsedId)) lastEventId = parsedId;
          }
          try {
            const parsed = JSON.parse(event.data);
            if (parsed.type === 'done') {
              callbacks.onDone({
                report: parsed.report,
                metrics: parsed.metrics || {},
                findings: parsed.findings || [],
              });
              activeEventSource?.close();
            } else {
              callbacks.onLog(parsed);
            }
          } catch (err) {
            console.warn('Failed to parse SSE agent_log:', err);
          }
        });

        activeEventSource.addEventListener('error', () => {
          activeEventSource?.close();
          if (isClosed) return;

          if (retryCount < maxRetries) {
            retryCount++;
            const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 8000);
            callbacks.onLog({
              agent: 'System',
              status: `Network connection interrupted. Resuming swarm stream from event #${lastEventId} (attempt ${retryCount}/${maxRetries})...`,
            });
            setTimeout(connectStream, delay);
          } else {
            callbacks.onError('Connection to Quorum multi-agent server lost after multiple retries.');
          }
        });
      };

      await connectStream();
    } catch (err: any) {
      if (!isClosed) {
        callbacks.onError(err.message || 'Failed to initialize research execution');
      }
    }
  })();

  return () => {
    isClosed = true;
    activeEventSource?.close();
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
 * Step 2 (HITL): Stream multi-agent execution with user-edited sub-questions.
 * Uses asynchronous job dispatch + reconnectable SSE stream with Last-Event-ID replay.
 */
export function streamResearchWithPlan(
  topic: string,
  customSubquestions: string[],
  callbacks: StreamCallbacks,
  depth: string = 'standard'
): () => void {
  let isClosed = false;
  let activeEventSource: EventSource | null = null;
  let lastEventId = 0;
  let retryCount = 0;
  const maxRetries = 5;

  (async () => {
    try {
      // Step 1: Create background research job
      const jobData = await createResearchJob(topic, customSubquestions, depth);
      if (isClosed) return;
      const jobId = jobData.job_id;

      // Step 2: Connect to reconnectable SSE stream with exponential backoff
      const connectStream = async () => {
        if (isClosed) return;

        let token = '';
        try {
          const { data } = await supabase.auth.getSession();
          token = data?.session?.access_token || '';
        } catch {}

        const tokenParam = token ? `&token=${encodeURIComponent(token)}` : '';
        const url = `${API_BASE}/api/jobs/${encodeURIComponent(jobId)}/stream?last_event_id=${lastEventId}${tokenParam}`;
        activeEventSource = new EventSource(url);

        activeEventSource.addEventListener('report_chunk', (event: MessageEvent) => {
          if (event.lastEventId) {
            const parsedId = parseInt(event.lastEventId, 10);
            if (!isNaN(parsedId)) lastEventId = parsedId;
          }
          try {
            const parsed = JSON.parse(event.data);
            if (parsed.chunk !== undefined && callbacks.onChunk) {
              callbacks.onChunk(parsed.chunk);
            }
          } catch (err) {
            console.warn('Failed to parse SSE report_chunk:', err);
          }
        });

        activeEventSource.addEventListener('agent_log', (event: MessageEvent) => {
          if (event.lastEventId) {
            const parsedId = parseInt(event.lastEventId, 10);
            if (!isNaN(parsedId)) lastEventId = parsedId;
          }
          try {
            const parsed = JSON.parse(event.data);
            if (parsed.type === 'done') {
              callbacks.onDone({
                report: parsed.report,
                metrics: parsed.metrics || {},
                findings: parsed.findings || [],
              });
              activeEventSource?.close();
            } else {
              callbacks.onLog(parsed);
            }
          } catch (err) {
            console.warn('Failed to parse SSE agent_log:', err);
          }
        });

        activeEventSource.addEventListener('error', () => {
          activeEventSource?.close();
          if (isClosed) return;

          if (retryCount < maxRetries) {
            retryCount++;
            const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 8000);
            callbacks.onLog({
              agent: 'System',
              status: `Network connection interrupted. Resuming swarm stream from event #${lastEventId} (attempt ${retryCount}/${maxRetries})...`,
            });
            setTimeout(connectStream, delay);
          } else {
            callbacks.onError('Connection to Quorum multi-agent server lost after multiple retries.');
          }
        });
      };

      await connectStream();
    } catch (err: any) {
      if (!isClosed) {
        callbacks.onError(err.message || 'Failed to initialize research execution');
      }
    }
  })();

  return () => {
    isClosed = true;
    activeEventSource?.close();
  };
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

/**
 * Export research report as Microsoft Word (.docx) document.
 */
export async function exportReportDocx(topic: string, markdownReport: string): Promise<Blob> {
  const headers = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/api/export_docx`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      topic,
      markdown_report: markdownReport,
    }),
  });

  if (!res.ok) {
    throw new Error('Failed to generate Word DOCX report from backend');
  }

  return await res.blob();
}

/**
 * Concurrently verify cited source URLs and retrieve domain reachability.
 */
export async function verifyCitations(urls: string[]): Promise<{ url: string; domain: string; status: 'verified' | 'unreachable'; status_code: number }[]> {
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_BASE}/api/verify_citations`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ urls }),
    });

    if (!res.ok) return [];
    const data = await res.json();
    return data.citations || [];
  } catch {
    return [];
  }
}

/**
 * Fetch real-time system metrics, latency percentiles, and Critic audit telemetry.
 */
export async function fetchSystemMetrics(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/api/metrics`, {
      method: 'GET',
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

