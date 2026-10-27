import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { Router, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { vi } from 'vitest';
import { Login } from './login';
import { Auth } from '../services/auth';

describe('Login', () => {
  let component: Login;
  let fixture: ComponentFixture<Login>;
  let auth: { login: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    auth = { login: vi.fn() };

    await TestBed.configureTestingModule({
      imports: [Login],
      providers: [
        provideRouter([]),
        { provide: Auth, useValue: auth },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(Login);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should subscribe to the auth check and navigate to chat on success', () => {
    auth.login.mockReturnValue(
      of({ userId: 'user-123', displayName: 'Test User', roles: [] }),
    );
    const router = TestBed.inject(Router);
    const navigateSpy = vi
      .spyOn(router, 'navigateByUrl')
      .mockResolvedValue(true);

    fixture.detectChanges();

    expect(auth.login).toHaveBeenCalledOnce();
    expect(navigateSpy).toHaveBeenCalledWith('/chat');
  });

  it('should show a sign-in message when the session is unauthorized', () => {
    auth.login.mockReturnValue(
      throwError(() => new HttpErrorResponse({ status: 401 })),
    );

    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Sign in with your organization account to continue.',
    );
  });
});
