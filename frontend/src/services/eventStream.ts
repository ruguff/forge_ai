import { BackendEvent } from '../types/office';

export interface EventSourceAdapter {
  connect(projectId: string): void;
  disconnect(): void;
  subscribe(callback: (event: BackendEvent) => void): () => void;
}

export class BackendEventSource implements EventSourceAdapter {
  private eventSource: EventSource | null = null;
  private listeners: Set<(event: BackendEvent) => void> = new Set();
  private isConnected = false;

  connect(projectId: string): void {
    if (this.eventSource) {
      this.disconnect();
    }

    try {
      const url = `/api/projects/${projectId}/stream`;
      this.eventSource = new EventSource(url);
      this.isConnected = true;

      this.eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          this.emit(parsed);
        } catch (err) {
          console.warn('[BackendEventSource] Failed to parse event data:', err);
        }
      };

      this.eventSource.onerror = (err) => {
        console.warn('[BackendEventSource] SSE connection encountered error:', err);
        this.isConnected = false;
      };
    } catch (err) {
      console.warn('[BackendEventSource] Failed to establish EventSource:', err);
      this.isConnected = false;
    }
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.isConnected = false;
  }

  subscribe(callback: (event: BackendEvent) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  private emit(event: BackendEvent): void {
    this.listeners.forEach((cb) => {
      try {
        cb(event);
      } catch (err) {
        console.error('[BackendEventSource] Listener callback threw error:', err);
      }
    });
  }

  public get connected(): boolean {
    return this.isConnected;
  }
}

export class MockEventSource implements EventSourceAdapter {
  private listeners: Set<(event: BackendEvent) => void> = new Set();
  private timer: number | null = null;
  private isRunning = false;

  connect(projectId: string): void {
    this.disconnect();
    this.isRunning = true;
    console.log(`[MockEventSource] Connected simulation for project ${projectId}`);
  }

  disconnect(): void {
    this.isRunning = false;
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }

  subscribe(callback: (event: BackendEvent) => void): () => void {
    this.listeners.add(callback);
    return () => this.listeners.delete(callback);
  }

  public dispatch(event: BackendEvent): void {
    if (!this.isRunning) return;
    this.listeners.forEach((cb) => {
      try {
        cb(event);
      } catch (err) {
        console.error('[MockEventSource] Listener callback error:', err);
      }
    });
  }
}

export function createEventSourceAdapter(preferBackend = true): EventSourceAdapter {
  if (preferBackend && typeof EventSource !== 'undefined') {
    return new BackendEventSource();
  }
  return new MockEventSource();
}
