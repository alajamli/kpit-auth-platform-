import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { logIcon, logKind, logText } from '../../core/utils/log-format';
import { TestManagementService } from '../../core/services/test-management.service';

@Component({
  selector: 'app-test-history',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatSnackBarModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './test-history.component.html',
  styleUrl: './test-history.component.scss'
})
export class TestHistoryComponent implements OnInit {
  loading = false;
  history: any[] = [];
  selectedJob: any = null;
  readonly logKind = logKind;
  readonly logText = logText;
  readonly logIcon = logIcon;

  displayedColumns = ['started_at', 'status', 'passed', 'failed', 'total', 'actions'];

  constructor(
    private testService: TestManagementService,
    private snackBar: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.loadHistory();
  }

  loadHistory(): void {
    this.loading = true;
    this.testService.getTestHistory().subscribe({
      next: (res) => {
        this.loading = false;
        this.history = res?.history || [];
      },
      error: () => {
        this.loading = false;
        this.snackBar.open('Failed to load test history', 'Close', { duration: 3000 });
      }
    });
  }

  openDetail(job: any): void {
    this.testService.getTestHistoryDetail(job.id).subscribe({
      next: (res) => {
        this.selectedJob = res?.job || job;
      },
      error: () => {
        this.snackBar.open('Failed to load job details', 'Close', { duration: 3000 });
      }
    });
  }

  closeDetail(): void {
    this.selectedJob = null;
  }
}