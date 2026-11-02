import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatRippleModule } from '@angular/material/core';
import { AuthService } from '../../services/auth.service';

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
  imports: [CommonModule, RouterModule, MatIconModule, MatRippleModule],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss'
})
export class SidebarComponent {

  
  @Input() collapsed = false;
  /** Ouverture en mode tiroir (mobile) — piloté par le layout */
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
          route: '',
          badge: { text: 'SOON', color: 'slate' }
        },
        {
          label: 'Test History',
          icon: 'history',
          route: '',
          badge: { text: 'SOON', color: 'slate' }
        }
      ]
    },
    {
      title: 'MANAGEMENT',
      items: [
        {
          label: 'Users',
          icon: 'people',
          route: '/users',
          
        },
        {
          label: 'Settings',
          icon: 'settings',
          route: '',
          badge: { text: 'SOON', color: 'slate' }
        }
      ]
    }
  ];

  constructor(private router: Router , private authService: AuthService) {

  }
  get filteredSections(): NavSection[] {
  const role = this.authService.getCurrentUser()?.role;
  return this.navigationSections.map(section => ({
    ...section,
    items: section.items.filter(item => {
      // Seuls les admins voient "Users"
      if (item.route === '/users') {
        return role === 'admin';
      }
      return true;
    })
  }));
}

  navigateTo (item: NavItem): void {
    if (item.route) {
      this.router.navigate([item.route]);
    }
  }

  isRouteActive(route: string | undefined): boolean {
    if (!route) return false;
    return this.router.url.startsWith(route);
  }
}