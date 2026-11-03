// src/app/core/components/sidebar/sidebar.component.ts

import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatRippleModule } from '@angular/material/core';
import { AuthService } from '../../services/auth.service';
import { BrandLogoComponent } from '../brand-logo/brand-logo.component';

interface NavItem {
  label: string;
  icon: string;
  route?: string;
  badge?: {
    text: string;
    color: string;
  };
}

interface NavSection {
  title: string;
  items: NavItem[];
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule, MatIconModule, MatRippleModule, BrandLogoComponent],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent {

  @Input() collapsed = false;
  @Input() mobileOpen = false;

  navigationSections: NavSection[] = [
    {
      title: 'DASHBOARDS',
      items: [
        {
          label: 'Overview',
          icon: 'insights',
          route: '/welcome'
        }
      ]
    },
    {
      title: 'TESTING',
      items: [
        {
          label: 'Test Cases',
          icon: 'fact_check',
          route: '/tests'
        },
        {
          label: 'Test Reports',
          icon: 'analytics',
          route: '/tests/reports'
        },
        {
          label: 'Test History',
          icon: 'history',
          route: '/tests/history'
        }
      ]
    },
    {
      title: 'MANAGEMENT',
      items: [
        {
          label: 'Users',
          icon: 'people',
          route: '/users'
        },
        {
          label: 'Settings',
          icon: 'settings',
          route: '/settings'
        }
      ]
    }
  ];

  constructor(private router: Router, private authService: AuthService) {}

  /* Display-only helpers for the user card (replaces the hard-coded demo user) */
  get fullName(): string {
    const u = this.authService.getCurrentUser();
    return u ? `${u.first_name} ${u.last_name}`.trim() : 'Guest';
  }

  get initials(): string {
    const u = this.authService.getCurrentUser();
    return u ? `${u.first_name?.charAt(0) ?? ''}${u.last_name?.charAt(0) ?? ''}`.toUpperCase() || 'U' : 'G';
  }

  get roleLabel(): string {
    const role = this.authService.getCurrentUser()?.role ?? 'viewer';
    return role.charAt(0).toUpperCase() + role.slice(1);
  }

  get filteredSections(): NavSection[] {
    const role = this.authService.getCurrentUser()?.role;
    return this.navigationSections.map(section => ({
      ...section,
      items: section.items.filter(item => {
        if (item.route === '/users') {
          return role === 'admin';
        }
        return true;
      })
    }));
  }

  navigateTo(item: NavItem): void {
    if (item.route) {
      this.router.navigate([item.route]);
    }
  }

  /**
   * FIX: Vérification exacte de l'URL pour éviter que /tests/reports
   * ne déclenche l'état actif sur la route /tests.
   */
  isRouteActive(route: string | undefined): boolean {
    if (!route) return false;
    
    // Nettoie l'URL actuelle en retirant les paramètres de requête s'il y en a (ex: ?page=1)
    const currentUrl = this.router.url.split('?')[0];
    
    return currentUrl === route;
  }
}