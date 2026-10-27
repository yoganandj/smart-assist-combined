import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  Router,
  RouterStateSnapshot,
  UrlTree,
  provideRouter,
} from '@angular/router';
import { firstValueFrom, isObservable, of, throwError } from 'rxjs';
import { vi } from 'vitest';
import { authGuard } from './auth-guard';
import { Auth } from '../services/auth';

describe('authGuard', () => {
  let auth: { login: ReturnType<typeof vi.fn> };

  beforeEach(() => {
    auth = { login: vi.fn() };
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: Auth, useValue: auth },
      ],
    });
  });

  it('allows navigation when Easy Auth confirms the session', async () => {
    auth.login.mockReturnValue(
      of({ userId: 'user-123', displayName: 'Test User', roles: [] }),
    );

    const guardResult = TestBed.runInInjectionContext(() =>
      authGuard(
        {} as ActivatedRouteSnapshot,
        { url: '/chat' } as RouterStateSnapshot,
      ),
    );
    const result = isObservable(guardResult)
      ? await firstValueFrom(guardResult)
      : await guardResult;

    expect(auth.login).toHaveBeenCalledOnce();
    expect(result).toBe(true);
  });

  it('redirects to login when Easy Auth does not confirm the session', async () => {
    auth.login.mockReturnValue(throwError(() => new Error('Unauthorized')));

    const guardResult = TestBed.runInInjectionContext(() =>
      authGuard(
        {} as ActivatedRouteSnapshot,
        { url: '/chat' } as RouterStateSnapshot,
      ),
    );
    const result = isObservable(guardResult)
      ? await firstValueFrom(guardResult)
      : await guardResult;

    expect(result).toBeInstanceOf(UrlTree);
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/login');
  });
});
