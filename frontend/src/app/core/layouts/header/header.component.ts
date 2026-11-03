import { Component, Output, EventEmitter, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NavigationEnd, Router } from '@angular/router';
import { Subscription, filter } from 'rxjs';

import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';

import { AuthService } from '../../services/auth.service';
import { ThemeService } from '../../services/theme.service';
import { AppNotification, NotificationService } from '../../services/notification.service';
import { User } from '../../models/auth.model';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    MatBadgeModule,
    MatDividerModule,
    MatTooltipModule
  ],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent implements OnInit, OnDestroy {
  @Output() menuToggle = new EventEmitter<void>();

  currentUser: User | null = null;
  notifications: AppNotification[] = [];
  pageTitle = 'Overview';

  private subs = new Subscription();

  /** Route → label shown in the top bar */
  private readonly titles: [string, string][] = [
    ['/tests/history', 'Test History'],
    ['/tests/reports', 'Test Reports'],
    ['/tests', 'Test Cases'],
    ['/users', 'User Directory'],
    ['/settings', 'Settings'],
    ['/welcome', 'Overview']
  ];

  constructor(
    private authService: AuthService,
    private router: Router,
    public theme: ThemeService,
    private notificationService: NotificationService
  ) {
    this.currentUser = this.authService.getCurrentUser();
  }

  ngOnInit(): void {
    this.updateTitle(this.router.url);
    this.subs.add(
      this.router.events
        .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
        .subscribe(e => this.updateTitle(e.urlAfterRedirects))
    );
    this.subs.add(this.notificationService.items$.subscribe(items => (this.notifications = items)));
    this.notificationService.startWatching();
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
    this.notificationService.stopWatching();
  }

  get unreadCount(): number {
    return this.notifications.filter(n => !n.read).length;
  }

  get initials(): string {
    const u = this.currentUser;
    return u ? `${u.first_name?.charAt(0) ?? ''}${u.last_name?.charAt(0) ?? ''}`.toUpperCase() || 'U' : 'U';
  }

  iconFor(n: AppNotification): string {
    switch (n.kind) {
      case 'success': return 'check_circle';
      case 'error': return 'error';
      case 'warning': return 'warning';
      default: return 'info';
    }
  }

  onNotificationsClosed(): void {
    this.notificationService.markAllRead();
  }

  clearNotifications(): void {
    this.notificationService.clear();
  }

  toggleMenu(): void {
    this.menuToggle.emit();
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  private updateTitle(url: string): void {
    const path = url.split('?')[0];
    const hit = this.titles.find(([prefix]) => path === prefix || path.startsWith(prefix + '/'));
    this.pageTitle = hit ? hit[1] : 'Overview';
  }
}
