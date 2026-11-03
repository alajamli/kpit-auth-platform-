import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Subscription, catchError, of, timer, switchMap } from 'rxjs';

import { TestManagementService } from './test-management.service';

export type NotificationKind = 'success' | 'error' | 'warning' | 'info';

export interface AppNotification {
  id: string;
  kind: NotificationKind;
  title: string;
  message: string;
  createdAt: number;
  read: boolean;
}

/**
 * In-app notification center (bell in the header).
 *
 * Read-only with regard to the platform: it never changes how tests run.
 * It only *observes* the existing GET /history endpoint and the anomaly score
 * already stored at login, and turns them into notifications.
 */
@Injectable({ providedIn: 'root' })
export class NotificationService implements OnDestroy {
  private readonly STORE_KEY = 'kpit-notifications';
  private readonly SEEN_KEY = 'kpit-notif-seen-jobs';
  private readonly MAX_ITEMS = 30;

  private readonly itemsSubject = new BehaviorSubject<AppNotification[]>(this.load());
  readonly items$ = this.itemsSubject.asObservable();

  private watcher?: Subscription;

  constructor(private testService: TestManagementService) {}

  get unreadCount(): number {
    return this.itemsSubject.value.filter(n => !n.read).length;
  }

  push(kind: NotificationKind, title: string, message: string, id?: string): void {
    const items = this.itemsSubject.value;
    const nid = id ?? `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    if (items.some(n => n.id === nid)) return;

    const next = [{ id: nid, kind, title, message, createdAt: Date.now(), read: false }, ...items]
      .slice(0, this.MAX_ITEMS);
    this.save(next);
  }

  markAllRead(): void {
    this.save(this.itemsSubject.value.map(n => ({ ...n, read: true })));
  }

  markRead(id: string): void {
    this.save(this.itemsSubject.value.map(n => (n.id === id ? { ...n, read: true } : n)));
  }

  clear(): void {
    this.save([]);
  }

  /** Start watching finished test executions (idempotent). */
  startWatching(): void {
    if (this.watcher) return;
    this.checkAnomalyScore();

    this.watcher = timer(4000, 30000)
      .pipe(
        switchMap(() => this.testService.getTestHistory().pipe(catchError(() => of(null))))
      )
      .subscribe(res => this.ingestHistory(res?.history));
  }

  stopWatching(): void {
    this.watcher?.unsubscribe();
    this.watcher = undefined;
  }

  ngOnDestroy(): void {
    this.stopWatching();
  }

  /* ---------------- internals ---------------- */

  private ingestHistory(history: any[] | undefined): void {
    if (!Array.isArray(history)) return;

    const seenRaw = this.readSeen();
    const firstRun = seenRaw === null;
    const seen = new Set<string>(seenRaw ?? []);

    for (const job of history) {
      if (!job?.id || seen.has(job.id)) continue;
      if (job.status !== 'completed' && job.status !== 'failed') continue;
      seen.add(job.id);
      if (firstRun) continue; // do not flood the bell with past runs on first load

      const total = job.total ?? 0;
      const passed = job.passed ?? 0;
      const failed = job.failed ?? 0;
      if (job.status === 'failed' || failed > 0) {
        this.push('error', 'Test run finished with failures', `${passed}/${total} passed · ${failed} failed`, `job-${job.id}`);
      } else {
        this.push('success', 'Test run passed', `${passed}/${total} tests passed`, `job-${job.id}`);
      }
    }
    this.writeSeen([...seen]);
  }

  private checkAnomalyScore(): void {
    try {
      const raw = localStorage.getItem('last_anomaly_score');
      const score = raw ? parseFloat(raw) : NaN;
      if (!isNaN(score) && score >= 0.65) {
        this.push(
          'warning',
          'Elevated sign-in risk',
          `The behavioural AI scored your last sign-in at ${Math.round(score * 100)}%.`,
          `anomaly-${raw}`
        );
      }
    } catch {
      /* ignore */
    }
  }

  private load(): AppNotification[] {
    try {
      const parsed = JSON.parse(localStorage.getItem(this.STORE_KEY) || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  private save(items: AppNotification[]): void {
    this.itemsSubject.next(items);
    try {
      localStorage.setItem(this.STORE_KEY, JSON.stringify(items));
    } catch {
      /* ignore */
    }
  }

  private readSeen(): string[] | null {
    try {
      const raw = localStorage.getItem(this.SEEN_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  private writeSeen(ids: string[]): void {
    try {
      localStorage.setItem(this.SEEN_KEY, JSON.stringify(ids.slice(-200)));
    } catch {
      /* ignore */
    }
  }
}
