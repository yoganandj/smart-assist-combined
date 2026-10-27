import { DOCUMENT } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface CurrentUser {
  userId: string;
  displayName: string;
  roles: string[];
}

@Injectable({ providedIn: 'root' })
export class Auth {
  constructor(
    private readonly http: HttpClient,
    @Inject(DOCUMENT) private readonly document: Document,
  ) {}

  login(): Observable<CurrentUser> {
    return this.http.get<CurrentUser>(`${environment.apiUrl}/auth/me`, {
      withCredentials: true,
    });
  }

  logout(): void {
    this.document.location.assign(
      '/.auth/logout?post_logout_redirect_uri=%2Flogin',
    );
  }
}
