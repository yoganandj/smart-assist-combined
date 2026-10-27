import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';
import { environment } from '../../environments/environment';

interface ChatResponse {
  reply: string;
}

export interface ApiChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface StreamEventPayload {
  delta?: string;
  detail?: string;
  status?: string;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  chat(message: string, history: ApiChatMessage[]): Observable<string> {
    return this.http
      .post<ChatResponse>(
        `${this.base}/chat`,
        { message, history },
        { withCredentials: true },
      )
      .pipe(map((r) => r.reply));
  }

  async streamChat(
    message: string,
    history: ApiChatMessage[],
    selectionType: 'FOSCodeBase' | 'FOSDocuments' | undefined,
    onDelta: (delta: string) => void
  ): Promise<void> {
    const response = await fetch(`${this.base}/chat/stream`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        history,
        selection_type: selectionType,
      }),
    });

    if (!response.ok) {
      throw new Error(await this.readError(response));
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Streaming response body is unavailable.');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
      buffer = buffer.replace(/\r\n/g, '\n');

      let boundary = buffer.indexOf('\n\n');
      while (boundary !== -1) {
        const rawEvent = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        const shouldStop = this.handleStreamEvent(rawEvent, onDelta);
        if (shouldStop) {
          await reader.cancel();
          return;
        }

        boundary = buffer.indexOf('\n\n');
      }

      if (done) {
        break;
      }
    }

    if (buffer.trim()) {
      this.handleStreamEvent(buffer, onDelta);
    }
  }

  private handleStreamEvent(
    rawEvent: string,
    onDelta: (delta: string) => void
  ): boolean {
    let eventName = 'message';
    const dataLines: string[] = [];

    for (const line of rawEvent.split('\n')) {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trim());
      }
    }

    if (dataLines.length === 0) {
      return false;
    }

    const payload = JSON.parse(dataLines.join('\n')) as StreamEventPayload;

    if (eventName === 'delta') {
      if (payload.delta) {
        onDelta(payload.delta);
      }
      return false;
    }

    if (eventName === 'error') {
      throw new Error(payload.detail || 'The assistant stream failed.');
    }

    return eventName === 'done';
  }

  private async readError(response: Response): Promise<string> {
    try {
      const payload = (await response.json()) as { detail?: string };
      return payload.detail || `Request failed with status ${response.status}.`;
    } catch {
      return `Request failed with status ${response.status}.`;
    }
  }
}
