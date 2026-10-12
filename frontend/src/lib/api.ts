/**
 * Quorum FastAPI Backend Client
 * Connects the frontend to the live Python multi-agent execution pipeline.
 */

export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

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
  const res = await fetch(`${API_BASE}/api/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
 * Uses native browser EventSource for robust, resilient streaming.
 */
export function streamResearchExecution(
  topic: string,
  callbacks: StreamCallbacks
): () => void {
  const url = `${API_BASE}/api/stream?topic=${encodeURIComponent(topic)}`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener('agent_log', (event: MessageEvent) => {
    try {
      const parsed = JSON.parse(event.data);
      if (parsed.type === 'done') {
        callbacks.onDone({
          report: parsed.report,
          metrics: parsed.metrics || {},
          findings: parsed.findings || [],
        });
        eventSource.close();
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
    eventSource.close();
  });

  return () => {
    eventSource.close();
  };
}

/**
 * Export research report as PDF via backend xhtml2pdf service.
 */
export async function exportReportPdf(topic: string, markdownReport: string): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/export_pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
