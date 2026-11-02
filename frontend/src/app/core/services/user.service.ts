import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  login: string;
  role: 'admin' | 'tester' | 'auditor' | 'viewer';
  is_verified?: boolean; // Status du compte (true = Active, false = Disabled)
  created_at?: string;
}

@Injectable({
  providedIn: 'root'
})
export class UserService {
  private apiUrl = `${environment.apiUrl}/users`;

  constructor(private http: HttpClient) {}

  getUsers(): Observable<{ success: boolean; users: User[] }> {
    return this.http.get<{ success: boolean; users: User[] }>(this.apiUrl);
  }

  createUser(userData: any): Observable<any> {
    return this.http.post<any>(this.apiUrl, userData);
  }

  updateUserRole(userId: number, role: string): Observable<any> {
    return this.http.patch<any>(`${this.apiUrl}/${userId}/role`, { role });
  }

  deleteUser(userId: number): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/${userId}`);
  }
  toggleUserStatus(userId: number): Observable<any> {
  return this.http.patch<any>(`${this.apiUrl}/${userId}/status`, {});
}
}