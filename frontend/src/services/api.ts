import { BackendEvent } from '../types/office';

export const API_BASE_URL = '';

async function request(path: string, body?: unknown, method = 'POST'): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/projects${path}`, {
    method, headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `Backend request failed (${response.status})`);
  return data;
}

export const createProject = (idea: string, mode: 'AUTONOMOUS' | 'GUIDED' = 'AUTONOMOUS') => request('', { idea, mode });
export const understandProject = (id: string) => request(`/${id}/understand`);
export const submitClarification = (id: string, questionId: string, answer: string) => request(`/${id}/clarify`, { question_id: questionId, answer });
export const fetchProjectContext = (id: string) => request(`/${id}/context`, undefined, 'GET');
export const submitIntakeAnswer = (id: string, questionId: string, answer: string) => request(`/${id}/intake`, { question_id: questionId, answer });
export const startPipelineAnalysis = (id: string) => request(`/${id}/analyze`);
export const compileBuildSpec = (id: string) => request(`/${id}/compile-spec`);
export const startAutonomousBuild = (id: string) => request(`/${id}/build`);
export const resolveProjectConflict = (id: string, conflictId: string, decision: string) => request(`/${id}/conflicts/${conflictId}/resolve`, { decision });

export async function openInEditor(id: string): Promise<{ success: boolean; message: string; workspace?: string }> {
  try { return await request(`/${id}/open-editor`); }
  catch (error) { return { success: false, message: String(error) }; }
}

export function subscribeToPipelineEvents(id: string, onEvent: (event: BackendEvent) => void, onError?: (error: any) => void): () => void {
  const source = new EventSource(`/api/projects/${id}/stream`);
  source.onmessage = event => {
    try { onEvent(JSON.parse(event.data)); }
    catch (error) { console.error('Invalid event', error); }
  };
  source.onerror = error => onError?.(error);
  return () => source.close();
}
