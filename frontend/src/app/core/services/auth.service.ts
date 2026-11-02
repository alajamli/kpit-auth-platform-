import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, BehaviorSubject } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  LoginRequest,
  RegisterRequest,
  LoginSuccessResponse,
  RegisterSuccessResponse,
  User
} from '../models/auth.model';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  private apiUrl = environment.apiUrl;

  private readonly USER_KEY = 'currentUser';
  private readonly TOKEN_KEY = 'access_token';

  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadUserFromStorage();
  }

    login(credentials: LoginRequest): Observable<LoginSuccessResponse> {
    const url = `${this.apiUrl}/auth/login`;

    return this.http.post<LoginSuccessResponse>(url, credentials).pipe(
      tap(response => {
        if (response.success && response.user) {
          this.saveUser(response.user);
          if (response.access_token) {
            this.saveToken(response.access_token);
          }
          // --- LAYER 2 : Stocker le score d'anomalie IA ---
          if (response.anomaly_score !== undefined) {
            localStorage.setItem('last_anomaly_score', response.anomaly_score.toString());
          }
        }
      }),
      catchError(this.handleError)
    );
  }

  register(userData: RegisterRequest): Observable<RegisterSuccessResponse> {
    const url = `${this.apiUrl}/auth/register`;
    return this.http.post<RegisterSuccessResponse>(url, userData).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Vérifie le token auprès du serveur (signature + user réel).
   * Utile pour tester JWT ; plus tard au bootstrap de l'app.
   */
  me(): Observable<{ success: boolean; user: User }> {
    return this.http.get<{ success: boolean; user: User }>(`${this.apiUrl}/auth/me`).pipe(
      tap(res => {
        if (res.success && res.user) {
          this.saveUser(res.user);
        }
      }),
      catchError(this.handleError)
    );
  }

  logout(): void {
    localStorage.removeItem(this.USER_KEY);
    localStorage.removeItem(this.TOKEN_KEY);
    this.currentUserSubject.next(null);
  }

  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }

  /** Token JWT pour l'interceptor */
  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  /**
   * Connecté = user local + access_token présent.
   * (Le serveur reste la source de vérité via @jwt_required plus tard.)
   */
  isAuthenticated(): boolean {
    return this.getCurrentUser() !== null && !!this.getToken();
  }

  private saveUser(user: User): void {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    this.currentUserSubject.next(user);
  }

  private saveToken(token: string): void {
    localStorage.setItem(this.TOKEN_KEY, token);
  }

  private loadUserFromStorage(): void {
    const userStr = localStorage.getItem(this.USER_KEY);
    if (userStr) {
      try {
        const user: User = JSON.parse(userStr);
        this.currentUserSubject.next(user);
      } catch {
        localStorage.removeItem(this.USER_KEY);
        localStorage.removeItem(this.TOKEN_KEY);
      }
    }
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred';

    if (error.error instanceof ErrorEvent) {
      errorMessage = `Client error: ${error.error.message}`;
    } else if (error.error && error.error.error) {
      errorMessage = error.error.error;
    } else if (error.status === 401) {
      errorMessage = 'Unauthorized — invalid or expired token';
    } else {
      errorMessage = `Server error: ${error.status} - ${error.statusText}`;
    }

    console.error('AuthService error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
   /**
   * Vérifier le code 2FA / OTP lors d'une connexion suspecte.
   */
  verify2FA(login: string, otpCode: string): Observable<LoginSuccessResponse> {
    const url = `${this.apiUrl}/auth/verify-2fa`;
    
    return this.http.post<LoginSuccessResponse>(url, { login, otp_code: otpCode }).pipe(
      tap(response => {
        if (response.success && response.access_token && response.user) {
          this.saveUser(response.user);
          this.saveToken(response.access_token);
        }
      }),
      catchError(this.handleError)
    );
  }

  resend2FA(login: string): Observable<{ success: boolean; message: string }> {
    const url = `${this.apiUrl}/auth/resend-2fa`;
    return this.http.post<{ success: boolean; message: string }>(url, { login }).pipe(
      catchError(this.handleError)
    );
  }
  loginWithGoogle(idToken: string): Observable<any> {
  return this.http.post<any>(`${this.apiUrl}/auth/google`, { id_token: idToken }).pipe(
    tap(response => {
      if (response.access_token) {
        localStorage.setItem('access_token', response.access_token);
        localStorage.setItem('refresh_token', response.refresh_token);
        localStorage.setItem('currentUser', JSON.stringify(response.user));
        this.currentUserSubject.next(response.user);
      }
    })
  );
}
}