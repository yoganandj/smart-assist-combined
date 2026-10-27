import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface CurrentUser {
  userId: string;
  displayName: string;
  roles: string[];
}

@Injectable({ providedIn: 'root' })
export class Auth {
  constructor(private readonly http: HttpClient) {}

  login(): Observable<CurrentUser> {
    return this.http.get<CurrentUser>(`${environment.apiUrl}/auth/me`, {
      withCredentials: true,
    });
  }
}
