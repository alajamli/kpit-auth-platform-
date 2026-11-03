import { Routes } from '@angular/router';
import { MainLayoutComponent } from './core/layouts/main-layout/main-layout.component';

export const routes: Routes = [
  // -------------------------------------------------------------
  // REDIRECTION INITIALE
  // -------------------------------------------------------------
  {
    path: '',
    redirectTo: 'login',
    pathMatch: 'full'
  },

  // -------------------------------------------------------------
  // AUTHENTICATION ROUTES (SANS SIDEBAR)
  // -------------------------------------------------------------
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then(m => m.LoginComponent),
    title: 'Login - KPIT Auth Platform'
  },
  {
    path: 'signup',
    loadComponent: () =>
      import('./features/auth/signup/signup.component').then(m => m.SignupComponent),
    title: 'Sign Up - KPIT Auth Platform'
  },

  // -------------------------------------------------------------
  // MAIN APP ROUTES (AVEC SIDEBAR & HEADER VEX)
  // -------------------------------------------------------------
  {
    path: '',
    component: MainLayoutComponent,
    children: [
      // 1. Dashboard
      {
        path: 'welcome',
        loadComponent: () =>
          import('./features/welcome/welcome.component').then(m => m.WelcomeComponent),
        title: 'Overview - KPIT Test Manager'
      },

      // 2. Testing Section
      {
        path: 'tests',
        loadComponent: () =>
          import('./features/test-management/test-management.component').then(
            m => m.TestManagementComponent
          ),
        title: 'Test Cases - KPIT Test Manager'
      },
      {
        path: 'tests/history',
        loadComponent: () =>
          import('./features/test-history/test-history.component').then(
            m => m.TestHistoryComponent
          ),
        title: 'Execution History - KPIT Test Manager'
      },
      {
        path: 'tests/reports',
        loadComponent: () =>
          import('./features/test-reports/test-reports.component').then(
            m => m.TestReportsComponent
          ),
        title: 'Test Reports - KPIT Test Manager'
      },

      // 3. Management Section
      {
        path: 'users',
        loadComponent: () =>
          import('./features/user-management/user-management.component').then(
            m => m.UserManagementComponent
          ),
        title: 'User Directory - KPIT Auth Platform'
      },
      
        {path: 'settings',
        loadComponent: () =>
          import('./features/settings/settings.component').then(
            m => m.SettingsComponent
          ),
        title: 'Settings - KPIT Auth Platform'
      }
    ]
  },

  // -------------------------------------------------------------
  // FALLBACK WILDCARD
  // -------------------------------------------------------------
  {
    path: '**',
    redirectTo: 'login'
  }
];