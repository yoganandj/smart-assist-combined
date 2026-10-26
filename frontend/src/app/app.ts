import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthService, ChatMessage, CurrentUser } from './auth.service';

@Component({
  imports: [FormsModule],
  selector: 'app-root',
  styleUrl: './app.css',
  templateUrl: './app.html',
})
export class App implements OnInit {
  protected readonly user = signal<CurrentUser | null>(null);
  protected readonly loading = signal(true);
  protected readonly sending = signal(false);
  protected readonly authError = signal<string | null>(null);
  protected readonly chatError = signal<string | null>(null);
  protected readonly chatNeedsLogin = signal(false);
  protected readonly messages = signal<ChatMessage[]>([]);
  protected draft = '';
  protected mode: 'code' | 'document' = 'code';

  constructor(private readonly authService: AuthService) {}

  ngOnInit(): void {
    this.loadUser();
  }

  protected loadUser(): void {
    this.loading.set(true);
    this.authError.set(null);

    this.authService.getCurrentUser().subscribe({
      next: (currentUser) => {
        this.user.set(currentUser);
        this.loading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.user.set(null);
        this.loading.set(false);
        if (error.status === 401) {
          this.authError.set('unauthenticated');
        } else if (error.status === 403) {
          this.authError.set('forbidden');
        } else {
          this.authError.set('Please check your connection and try again.');
        }
      },
    });
  }

  protected login(): void {
    window.location.assign('/.auth/login/aad?post_login_redirect_uri=%2F');
  }

  protected logout(): void {
    window.location.assign('/.auth/logout?post_logout_redirect_uri=%2F');
  }

  protected sendMessage(): void {
    const message = this.draft.trim();
    if (!message || this.sending()) {
      return;
    }

    const history = this.messages().map(({ role, content }) => ({ role, content }));
    this.messages.update((messages) => [...messages, { role: 'user', content: message }]);
    this.draft = '';
    this.chatError.set(null);
    this.chatNeedsLogin.set(false);
    this.sending.set(true);

    this.authService.sendMessage(message, history, this.mode).subscribe({
      next: (response) => {
        this.messages.update((messages) => [...messages, { role: 'assistant', content: response.reply }]);
        this.sending.set(false);
        this.chatNeedsLogin.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.sending.set(false);
        this.chatNeedsLogin.set(error.status === 401);
        this.chatError.set(
          error.status === 401
            ? 'Your session has expired. Sign in again to continue.'
            : error.status === 403
              ? 'Your account is not authorized to use this assistant.'
              : 'The assistant could not respond. Please try again.',
        );
      },
    });
  }

  protected clearConversation(): void {
    this.messages.set([]);
    this.chatError.set(null);
    this.chatNeedsLogin.set(false);
  }

  protected onComposerKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }
}
