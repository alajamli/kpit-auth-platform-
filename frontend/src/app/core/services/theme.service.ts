import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

/**
 * Light / dark mode.
 * The initial value is applied by an inline script in index.html (no flash);
 * this service only keeps the <html data-theme> attribute and localStorage in sync.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly STORAGE_KEY = 'kpit-theme';
  private readonly darkSubject = new BehaviorSubject<boolean>(this.readInitial());

  readonly isDark$ = this.darkSubject.asObservable();

  constructor() {
    this.apply(this.darkSubject.value);
  }

  get isDark(): boolean {
    return this.darkSubject.value;
  }

  toggle(): void {
    this.set(!this.darkSubject.value);
  }

  set(dark: boolean): void {
    this.darkSubject.next(dark);
    this.apply(dark);
    try {
      localStorage.setItem(this.STORAGE_KEY, dark ? 'dark' : 'light');
    } catch {
      /* storage unavailable – theme still applies for this session */
    }
  }

  private readInitial(): boolean {
    try {
      const saved = localStorage.getItem(this.STORAGE_KEY);
      if (saved) return saved === 'dark';
    } catch {
      /* ignore */
    }
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
  }

  private apply(dark: boolean): void {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  }
}
