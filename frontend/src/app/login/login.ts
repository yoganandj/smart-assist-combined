import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Auth } from '../services/auth';

@Component({
  selector: 'app-login',
  imports: [],
  templateUrl: './login.html',
  styleUrl: './login.css',
})
export class Login implements OnInit {
  protected isCheckingSession = true;
  protected errorMessage = '';

  constructor(
    private readonly auth: Auth,
    private readonly router: Router,
  ) {}

  ngOnInit(): void {
    this.auth.login().subscribe({
      next: () => {
        void this.router.navigateByUrl('/chat');
      },
      error: (error: HttpErrorResponse) => {
        this.isCheckingSession = false;

        if (error.status === 401) {
          this.errorMessage = 'Sign in with your organization account to continue.';
        } else if (error.status === 403) {
          this.errorMessage = 'Your account does not have access to this application.';
        } else {
          this.errorMessage = 'Unable to verify your session. Please try again.';
        }
      },
    });
  }
}
