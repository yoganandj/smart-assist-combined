import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { Auth } from './auth';
import { environment } from '../../environments/environment';

describe('Auth', () => {
  let service: Auth;
  let httpTestingController: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(Auth);
    httpTestingController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTestingController.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should return the current user from the auth endpoint', () => {
    const currentUser = {
      userId: 'user-123',
      displayName: 'Test User',
      roles: ['assistant-user'],
    };
    let receivedUser: typeof currentUser | undefined;

    service.login().subscribe((user) => {
      receivedUser = user;
    });

    const request = httpTestingController.expectOne(
      `${environment.apiUrl}/auth/me`,
    );
    expect(request.request.method).toBe('GET');
    request.flush(currentUser);

    expect(receivedUser).toEqual(currentUser);
  });
});
