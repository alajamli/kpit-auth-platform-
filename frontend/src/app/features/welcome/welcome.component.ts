import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';

import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';

import { catchError, forkJoin, of, Subscription } from 'rxjs';
import { User } from '../../core/models/auth.model';
import { AuthService } from '../../core/services/auth.service';
import { TestManagementService } from '../../core/services/test-management.service';

interface ChartBar {
  x: number;
  w: number;
  passY: number;
  passH: number;
  failY: number;
  failH: number;
  label: string;
  tip: string;
}

interface SuiteStat { name: string; count: number; pct: number; }
interface TagStat { tag: string; count: number; weight: number; }

@Component({
  selector: 'app-welcome',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatTooltipModule
  ],
  templateUrl: './welcome.component.html',
  styleUrl: './welcome.component.scss'
})
export class WelcomeComponent implements OnInit, OnDestroy {
  user: User | null = null;
  loginTime = new Date();
  greeting = 'Welcome';

  // Données dynamiques du backend
  totalTests = 0;
  totalSuites = 0;
  totalTags = 0;
  isLoadingStats = true;

  // Animated (count-up) values shown in the KPI cards
  shownTests = 0;
  shownSuites = 0;
  shownTags = 0;
  shownRate = 0;

  // --- Run history (read-only, from the existing /history endpoint) ---
  recentRuns: any[] = [];
  chartBars: ChartBar[] = [];
  readonly chartHeight = 150;
  passRate = 0;
  lastRunRate = 0;
  hasRuns = false;
  totalRuns = 0;

  // --- Coverage (derived from the existing /cases + /suites endpoints) ---
  suiteStats: SuiteStat[] = [];
  tagStats: TagStat[] = [];

  // --- LAYER 2 : MACHINE LEARNING ANOMALY SCORE ---
  anomalyScore = 0.10;  // Valeur par défaut
  isAnomaly = false;
  readonly gaugeLength = 251.3;

  private dataSub!: Subscription;

  constructor(
    private authService: AuthService,
    private testService: TestManagementService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.user = this.authService.getCurrentUser();
    if (!this.user) {
      this.router.navigate(['/login']);
      return;
    }

    const hour = new Date().getHours();
    this.greeting = hour < 5 ? 'Working late' : hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

    // Récupérer le dernier score d'anomalie stocké lors du login
    const storedScore = localStorage.getItem('last_anomaly_score');
    if (storedScore) {
      this.anomalyScore = parseFloat(storedScore);
      this.isAnomaly = this.anomalyScore >= 0.65;
    }

    this.loadRealDashboardData();
  }

  get gaugeOffset(): number {
    return this.gaugeLength * (1 - Math.min(Math.max(this.anomalyScore, 0), 1));
  }

  get riskLabel(): string {
    if (this.anomalyScore >= 0.65) return 'High';
    if (this.anomalyScore >= 0.35) return 'Moderate';
    return 'Low';
  }

  get donutDash(): string {
    const c = 2 * Math.PI * 52;
    return `${(c * this.passRate) / 100} ${c}`;
  }

  loadRealDashboardData(): void {
    this.dataSub = forkJoin({
      casesData: this.testService.getAllTestCases(),
      suitesData: this.testService.getSuites(),
      // history is optional: a failure here must never break the dashboard
      history: this.testService.getTestHistory().pipe(catchError(() => of(null)))
    }).subscribe({
      next: (results) => {
        this.totalTests = results.casesData.count;
        this.totalTags = results.casesData.available_tags.length;
        this.totalSuites = results.suitesData.count;
        this.isLoadingStats = false;

        this.buildCoverage(results.casesData.test_cases || []);
        this.buildHistory(results.history?.history || []);

        this.countUp('shownTests', this.totalTests);
        this.countUp('shownSuites', this.totalSuites);
        this.countUp('shownTags', this.totalTags);
        this.countUp('shownRate', this.passRate);
      },
      error: (err) => {
        console.error('Failed to load dashboard data', err);
        this.isLoadingStats = false;
      }
    });
  }

  /* ---------------- derived view-models ---------------- */

  private buildCoverage(cases: any[]): void {
    const bySuite = new Map<string, number>();
    const byTag = new Map<string, number>();
    for (const t of cases) {
      bySuite.set(t.file_name, (bySuite.get(t.file_name) || 0) + 1);
      for (const tag of t.tags || []) byTag.set(tag, (byTag.get(tag) || 0) + 1);
    }

    const maxSuite = Math.max(1, ...bySuite.values());
    this.suiteStats = [...bySuite.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, count]) => ({ name, count, pct: Math.round((count / maxSuite) * 100) }));

    const maxTag = Math.max(1, ...byTag.values());
    this.tagStats = [...byTag.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([tag, count]) => ({ tag, count, weight: Math.ceil((count / maxTag) * 3) }));
  }

  private buildHistory(history: any[]): void {
    const finished = history
      .filter(j => (j.status === 'completed' || j.status === 'failed') && (j.total || 0) > 0)
      .sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime());

    this.hasRuns = finished.length > 0;
    this.totalRuns = history.length;
    this.recentRuns = [...history]
      .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
      .slice(0, 5);

    if (!this.hasRuns) return;

    const sumPassed = finished.reduce((s, j) => s + (j.passed || 0), 0);
    const sumTotal = finished.reduce((s, j) => s + (j.total || 0), 0);
    this.passRate = sumTotal ? Math.round((sumPassed / sumTotal) * 100) : 0;

    const last = finished[finished.length - 1];
    this.lastRunRate = last.total ? Math.round((last.passed / last.total) * 100) : 0;

    const slice = finished.slice(-10);
    const maxTotal = Math.max(1, ...slice.map(j => j.total || 0));
    const slot = 600 / Math.max(slice.length, 6);
    const barW = Math.min(44, Math.round(slot * 0.55));
    this.chartBars = slice.map((j, i) => {
      const passH = Math.round(((j.passed || 0) / maxTotal) * this.chartHeight);
      const failH = Math.round(((j.failed || 0) / maxTotal) * this.chartHeight);
      const d = new Date(j.started_at);
      return {
        x: i * slot + (slot - barW) / 2,
        w: barW,
        passH,
        passY: this.chartHeight - passH,
        failH,
        failY: this.chartHeight - passH - failH,
        label: `${d.getDate()}/${d.getMonth() + 1}`,
        tip: `${d.toLocaleString()} — ${j.passed}/${j.total} passed, ${j.failed} failed`
      };
    });
  }

  private countUp(key: 'shownTests' | 'shownSuites' | 'shownTags' | 'shownRate', target: number): void {
    const duration = 900;
    const t0 = performance.now();
    const step = (t: number) => {
      const p = Math.min((t - t0) / duration, 1);
      this[key] = Math.round(target * (1 - Math.pow(1 - p, 3)));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  /* ---------------- navigation ---------------- */

  goToTestManagement(): void {
    this.router.navigate(['/tests']);
  }

  goToReports(): void {
    this.router.navigate(['/tests/reports']);
  }

  goToHistory(): void {
    this.router.navigate(['/tests/history']);
  }

  onLogout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  ngOnDestroy(): void {
    if (this.dataSub) {
      this.dataSub.unsubscribe();
    }
  }
}
