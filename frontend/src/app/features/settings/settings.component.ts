import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { ThemeService } from '../../core/services/theme.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatSlideToggleModule,
    MatSnackBarModule
  ],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss'
})
export class SettingsComponent implements OnInit {
  currentUser: any = null;
  autoExpandLogs = true;
  darkMode = false;

  constructor(
    private authService: AuthService,
    private snackBar: MatSnackBar,
    public theme: ThemeService
  ) {}

  ngOnInit(): void {
    this.currentUser = this.authService.getCurrentUser();
  }

  get initials(): string {
    const u = this.currentUser;
    return u ? `${u.first_name?.charAt(0) ?? ''}${u.last_name?.charAt(0) ?? ''}`.toUpperCase() || 'U' : 'U';
  }

  /** Display-only summary of what the current role may do (mirrors the existing guards). */
  get permissions(): { label: string; allowed: boolean }[] {
    const role = this.currentUser?.role;
    const canRun = role === 'admin' || role === 'tester';
    const isAdmin = role === 'admin';
    return [
      { label: 'View test cases, reports and history', allowed: true },
      { label: 'Run tests and generate them with AI', allowed: canRun },
      { label: 'Create, edit and delete test cases', allowed: isAdmin },
      { label: 'Manage users and roles', allowed: isAdmin }
    ];
  }

  setTheme(dark: boolean): void {
    this.theme.set(dark);
  }

  savePreferences(): void {
    this.snackBar.open('Preferences saved successfully!', 'Close', {
      duration: 3000
    });
  }

  clearLocalStorage(): void {
    localStorage.clear();
    this.snackBar.open('Local cache cleared. Please refresh if needed.', 'Close', {
      duration: 3000
    });
  }
}