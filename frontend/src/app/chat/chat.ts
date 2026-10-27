import { Component } from '@angular/core';
import { Auth } from '../services/auth';

@Component({
  imports: [],
  selector: 'app-chat',
  styleUrl: './chat.css',
  templateUrl: './chat.html',
})
export class Chat {
  constructor(private readonly auth: Auth) {}

  logout(): void {
    this.auth.logout();
  }
}
