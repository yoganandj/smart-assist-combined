import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface CurrentUser {
  userId: string;
  displayName: string;
  roles: string[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatResponse {
  reply: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  constructor(private readonly http: HttpClient) {}

  getCurrentUser(): Observable<CurrentUser> {
    return this.http.get<CurrentUser>('/auth/me', { withCredentials: true });
  }

  sendMessage(
    message: string,
    history: ChatMessage[],
    mode: 'code' | 'document',
  ): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(
      '/chat',
      { message, history, mode },
      { withCredentials: true },
    );
  }
}
