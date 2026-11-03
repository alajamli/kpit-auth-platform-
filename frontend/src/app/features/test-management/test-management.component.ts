import { logIcon, logKind, logText } from '../../core/utils/log-format';
import { environment } from '../../../environments/environment';
import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

// Angular Material
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatBadgeModule } from '@angular/material/badge';
import { MatDividerModule } from '@angular/material/divider';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule } from '@angular/material/sort';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';


import { Subscription } from 'rxjs';
import { TestCaseDialogComponent } from './test-case-dialog/test-case-dialog.component';
import { User } from '../../core/models/auth.model';
import { TestCase, JobStatus, RunTestsResponse, TestResult } from '../../core/models/test.model';
import { AuthService } from '../../core/services/auth.service';
import { TestManagementService } from '../../core/services/test-management.service';

@Component({
  selector: 'app-test-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatCheckboxModule,
    MatChipsModule,
    MatProgressBarModule,
    MatTooltipModule,
    MatSnackBarModule,
    MatToolbarModule,
    MatMenuModule,
    MatSidenavModule,
    MatListModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatBadgeModule,
    MatDividerModule,
    MatTableModule,
    MatSortModule,
    MatButtonToggleModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatPaginatorModule
  ],
  templateUrl: './test-management.component.html',
  styleUrl: './test-management.component.scss'
})
export class TestManagementComponent implements OnInit, OnDestroy {
  // Données
  viewMode: 'boxed' | 'fullwidth' = 'boxed';
  allTestCases: TestCase[] = [];
  filteredTestCases: TestCase[] = [];
  pagedTestCases: TestCase[] = [];
  availableTags: string[] = [];
  suites: string[] = [];
  currentUser: User | null = null;
  currentJob: JobStatus | null = null;
  pollSubscription: Subscription | null = null;
  elapsedSeconds = 0;
  elapsedInterval: any = null;
  
  // État d'annulation explicite (Garantit que le résultat ne sera jamais écrasé)
  isJobCancelled = false;

  // Pagination
  pageSize = 10;
  pageIndex = 0;

  // Filtres
  searchTerm = '';
  selectedSuite = 'all';
  selectedTags: string[] = [];
  selectedStatus = 'all';
  
  // État
  isLoading = false;
  isRunning = false;
  showResultsPanel = false;
  
  // Results
  lastResults: RunTestsResponse | null = null;

  // AI Test Generator — generalized for any target URL / credentials (Step 1.3)
  aiRequirement: string = '';
  targetUrl: string = '';
  testData: string = '';
  isGenerating: boolean = false;
  generatedCode: string = '';
  aiProvider: string = 'groq';
  constructor(
    private testService: TestManagementService,
    private authService: AuthService,
    private router: Router,
    private snackBar: MatSnackBar,
    private dialog: MatDialog 
  ) {}

  ngOnInit(): void {
    this.currentUser = this.authService.getCurrentUser();
    if (!this.currentUser) {
      this.router.navigate(['/login']);
      return;
    }
    this.loadTests();
  }

  loadTests(): void {
    this.isLoading = true;
    
    this.testService.getAllTestCases().subscribe({
      next: (response) => {
        this.allTestCases = response.test_cases.map(tc => ({
          ...tc,
          selected: false,
          lastStatus: null
        }));
        this.availableTags = response.available_tags;
        this.extractSuites();
        this.applyFilters();
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading tests:', error);
        this.isLoading = false;
        this.showMessage('Failed to load tests', 'error');
      }
    });
  }

  private extractSuites(): void {
    const suitesSet = new Set<string>();
    this.allTestCases.forEach(tc => suitesSet.add(tc.file_name));
    this.suites = Array.from(suitesSet).sort();
  }
    // ============================================
  // RBAC GETTERS (Contrôle d'affichage IHM)
  // ============================================

  /**
   * Retourne le rôle courant en minuscules (ex: 'admin', 'tester', 'viewer')
   */
  get userRole(): string {
    return this.currentUser?.role?.toLowerCase() || 'viewer';
  }

  /**
   * Seul l'ADMIN a accès à la gestion complète (Créer, Modifier, Supprimer)
   */
  get canManageTests(): boolean {
    return this.userRole === 'admin';
  }

  /**
   * L'ADMIN et le TESTER ont le droit d'exécuter des tests
   */
  get canRunTests(): boolean {
    return this.userRole === 'admin' || this.userRole === 'tester';
  }

  /**
   * Le VIEWER est en lecture seule absolue
   */
  get isReadOnly(): boolean {
    return this.userRole === 'viewer';
  }

  // ============ FILTRES & PAGINATION ============
  
  applyFilters(): void {
    let filtered = [...this.allTestCases];
    
    if (this.searchTerm.trim()) {
      const term = this.searchTerm.toLowerCase();
      filtered = filtered.filter(t => 
        t.name.toLowerCase().includes(term) ||
        t.id.toLowerCase().includes(term) ||
        t.documentation.toLowerCase().includes(term)
      );
    }
    
    if (this.selectedSuite !== 'all') {
      filtered = filtered.filter(t => t.file_name === this.selectedSuite);
    }
    
    if (this.selectedTags.length > 0) {
      filtered = filtered.filter(t => 
        this.selectedTags.some(tag => t.tags.includes(tag))
      );
    }
    
    if (this.selectedStatus === 'passed') {
      filtered = filtered.filter(t => t.lastStatus === 'PASS');
    } else if (this.selectedStatus === 'failed') {
      filtered = filtered.filter(t => t.lastStatus === 'FAIL');
    } else if (this.selectedStatus === 'not-run') {
      filtered = filtered.filter(t => !t.lastStatus);
    }
    
    this.filteredTestCases = filtered;
    this.pageIndex = 0;
    this.updatePage();
  }

  clearFilters(): void {
    this.searchTerm = '';
    this.selectedSuite = 'all';
    this.selectedTags = [];
    this.selectedStatus = 'all';
    this.applyFilters();
  }

  onPageChange(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.updatePage();
  }

  updatePage(): void {
    const start = this.pageIndex * this.pageSize;
    this.pagedTestCases = this.filteredTestCases.slice(start, start + this.pageSize);
  }

  // ============ SÉLECTION ============
  
  getSelectedCount(): number {
    return this.allTestCases.filter(t => t.selected).length;
  }
  
  getSelectedTests(): TestCase[] {
    return this.allTestCases.filter(t => t.selected);
  }
  
  areAllFilteredSelected(): boolean {
    return this.pagedTestCases.length > 0 && 
           this.pagedTestCases.every(t => t.selected);
  }
  
  toggleSelectAll(): void {
    const shouldSelect = !this.areAllFilteredSelected();
    this.pagedTestCases.forEach(t => t.selected = shouldSelect);
  }

  // ============ EXÉCUTION ============
  
  runSelectedTests(): void {
    const selected = this.getSelectedTests();
    if (selected.length === 0) {
      this.showMessage('Please select at least one test', 'warning');
      return;
    }
    const testNames = selected.map(t => t.name);
    this.executeTests({ test_names: testNames });
  }
  
  runAllTests(): void {
    if (this.filteredTestCases.length === 0) {
      this.showMessage('No tests available to run with current filters', 'warning');
      return;
    }
    const testNames = this.filteredTestCases.map(t => t.name);
    this.executeTests({ test_names: testNames });
  }
  
  runFailedTests(): void {
    const failedTests = this.allTestCases.filter(t => t.lastStatus === 'FAIL');
    if (failedTests.length === 0) {
      this.showMessage('No failed tests to re-run', 'info');
      return;
    }
    const testNames = failedTests.map(t => t.name);
    this.executeTests({ test_names: testNames });
  }
  
  runSingleTest(test: TestCase): void {
    this.executeTests({ test_names: [test.name] });
  }
  
  private executeTests(request: any): void {
    this.isRunning = true;
    this.isJobCancelled = false; // Réinitialiser le statut d'annulation
    this.lastResults = null;
    this.currentJob = null;
    this.elapsedSeconds = 0;
    
    this.elapsedInterval = setInterval(() => {
      this.elapsedSeconds++;
    }, 1000);
    
    this.testService.runTestsAsync(request).subscribe({
      next: (response) => {
        this.startPolling(response.job_id);
      },
      error: (error) => {
        console.error('Failed to start tests:', error);
        this.isRunning = false;
        clearInterval(this.elapsedInterval);
        this.showMessage('Failed to start tests', 'error');
      }
    });
  }

    private startPolling(jobId: string): void {
    this.pollSubscription = this.testService.pollJobStatus(jobId, 500).subscribe({
      next: (response) => {
        // Ne pas écraser si annulé localement
        if (!this.isJobCancelled) {
          this.currentJob = response.job;
          
          setTimeout(() => {
            const logsContainer = document.querySelector('.logs-container');
            if (logsContainer) {
              logsContainer.scrollTop = logsContainer.scrollHeight;
            }
          }, 50);
          
          if (response.job.status === 'completed' || response.job.status === 'failed') {
            this.onJobCompleted(response.job);
          }
        }
      },
      error: (error) => {
        console.error('Polling error:', error);
        if (!this.isJobCancelled) {
          this.isRunning = false;
          clearInterval(this.elapsedInterval);
          this.showMessage('Error while polling test status', 'error');
        }
      }
    });
  }

  private onJobCompleted(job: JobStatus): void {
    // 1. Arrêter le chrono et couper le polling HTTP
    clearInterval(this.elapsedInterval);
    if (this.pollSubscription) {
      this.pollSubscription.unsubscribe();
    }

    // 2. Conserver exactement vos appels d'origine
    this.updateTestStatuses(job.tests);
    this.updatePage();
    
    this.lastResults = {
      success: job.failed === 0 && job.total > 0 && !this.isJobCancelled,
      total: job.total,
      passed: job.passed,
      failed: job.failed,
      return_code: job.status === 'completed' ? 0 : 1,
      tests: job.tests,
      report_available: job.report_available
    };
  }

  // ANNULATION DÉFINITIVE & STABLE
  cancelTests(): void {
    if (!this.currentJob?.id) return;

    const jobId = this.currentJob.id;
    
    // 1. Marquer immédiatement comme annulé
    this.isJobCancelled = true;
    
    // 2. STOPPER LE POLLING ET LE CHRONO IMMÉDIATEMENT
    if (this.pollSubscription) {
      this.pollSubscription.unsubscribe();
    }
    if (this.elapsedInterval) {
      clearInterval(this.elapsedInterval);
    }

    // 3. Forcer l'état de l'overlay local
    if (this.currentJob) {
      this.currentJob = {
        ...this.currentJob,
        status: 'failed',
        error: 'Execution cancelled by user',
        current_test: null
      };
    }

    // 4. Appeler l'API Backend pour tuer Chrome
    this.testService.cancelJob(jobId).subscribe({
      next: () => {
        console.log('Backend kill command sent');
      },
      error: (err) => {
        console.error('Cancel API error:', err);
      }
    });
  }

  openReport(): void {
    // same base as every other API call: '/api' behind nginx (Docker), localhost:5000 in dev
    const reportUrl = `${environment.apiUrl}/tests/report`;
    window.open(reportUrl, '_blank');
  }

  closeOverlay(): void {
    this.isRunning = false;
    
    if (this.isJobCancelled) {
      this.showMessage('Test execution was cancelled', 'warning');
    } else if (this.lastResults) {
      const message = this.lastResults.failed === 0
        ? `All ${this.lastResults.passed} tests passed in ${this.formatElapsed()}`
        : `${this.lastResults.passed}/${this.lastResults.total} passed, ${this.lastResults.failed} failed`;
      
      this.showMessage(message, this.lastResults.failed === 0 ? 'success' : 'warning');
    }

    this.currentJob = null;
    this.isJobCancelled = false;
  }

  formatElapsed(): string {
    const minutes = Math.floor(this.elapsedSeconds / 60);
    const seconds = this.elapsedSeconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }

  getProgressPercent(): number {
    if (!this.currentJob || this.currentJob.total === 0) return 0;
    const percent = Math.round((this.currentJob.completed / this.currentJob.total) * 100);
    return Math.min(percent, 100);
  }
  
  private updateTestStatuses(results: TestResult[]): void {
    for (const result of results) {
      const test = this.allTestCases.find(t => 
        result.name.includes(t.name) || t.name.includes(result.name)
      );
      if (test) {
        test.lastStatus = result.status;
      }
    }
  }

  // ============ HELPERS & UTILS ============
  
  goToWelcome(): void {
    this.router.navigate(['/welcome']);
  }
  
  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }
  
  refresh(): void {
    this.loadTests();
  }

  getStatusIcon(status: string | null | undefined): string {
    if (status === 'PASS') return 'check_circle';
    if (status === 'FAIL') return 'cancel';
    return 'radio_button_unchecked';
  }

  private showMessage(message: string, type: 'success' | 'error' | 'warning' | 'info'): void {
    this.snackBar.open(message, 'Close', {
      duration: type === 'error' ? 5000 : 3000,
      panelClass: [`snackbar-${type}`],
      horizontalPosition: 'right',
      verticalPosition: 'top'
    });
  }

  getTagClass(tag: string): string {
    const tagMap: { [key: string]: string } = {
      'smoke': 'label-primary',
      'critical': 'label-primary',
      'success': 'label-green',
      'e2e': 'label-green',
      'api': 'label-cyan',
      'ui': 'label-purple',
      'auth': 'label-purple',
      'error': 'label-orange',
      'security': 'label-orange',
      'regression': 'label-teal'
    };
    return tagMap[tag] || 'label-primary';
  }

  /** Number of filters currently applied (shown as a badge on the Filters button). */
  get activeFilterCount(): number {
    return (this.selectedSuite !== 'all' ? 1 : 0) +
           (this.selectedStatus !== 'all' ? 1 : 0) +
           (this.selectedTags.length ? 1 : 0);
  }

  // Log display helpers (emoji -> icon), see core/utils/log-format.ts
  readonly logKind = logKind;
  readonly logText = logText;
  readonly logIcon = logIcon;

  hasActiveFilters(): boolean {
    return this.selectedSuite !== 'all' || 
           this.selectedStatus !== 'all' || 
           this.selectedTags.length > 0 ||
           this.searchTerm.trim() !== '';
  }

  ngOnDestroy(): void {
    if (this.pollSubscription) {
      this.pollSubscription.unsubscribe();
    }
    if (this.elapsedInterval) {
      clearInterval(this.elapsedInterval);
    }
  }

  // ============ CRUD OPERATIONS ============

  openAddTestDialog(initialTab?: 'ai'): void {
    const dialogRef = this.dialog.open(TestCaseDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      autoFocus: false,
      restoreFocus: true,
      panelClass: 'vex-dialog-panel',
      data: {
        mode: 'add',
        initialTab: initialTab,
        aiOnly: initialTab === 'ai' && !this.canManageTests,
        suiteName: (this.suites && this.suites.length ? this.suites[0] : ''),
        suites: this.suites || [],
        availableTags: this.availableTags && this.availableTags.length 
          ? this.availableTags 
          : ['smoke', 'regression', 'api', 'ui', 'custom']
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (!result) return;

      // 1. Si le test a été généré et sauvegardé via l'IA (Groq)
      if (result.type === 'ai_saved') {
        this.loadTests();
        return;
      }

      // 2. Si le test a été créé manuellement
      if (result.type === 'manual' || result.suiteName) {
        this.isLoading = true;
        this.testService.addTestCase(result.suiteName, result.data).subscribe({
          next: () => {
            this.showMessage('Test case created successfully', 'success');
            this.loadTests();
          },
          error: (err) => {
            this.isLoading = false;
            this.showMessage(`Failed to create test: ${err.error?.error || err.message}`, 'error');
          }
        });
      }
    });
  }

    openEditTestDialog(test: TestCase): void {
    const dialogRef = this.dialog.open(TestCaseDialogComponent, {
      width: '680px',
      maxWidth: '95vw',
      autoFocus: false,
      restoreFocus: true,
      panelClass: 'vex-dialog-panel',
      data: {
        mode: 'edit',
        testCase: test,
        suiteName: test.file_name,
        suites: this.suites || [],
        availableTags: this.availableTags.length
          ? this.availableTags
          : ['smoke', 'regression', 'api', 'ui', 'custom']
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.isLoading = true;
        this.testService.updateTestCase(test.file_name, test.id, result.data).subscribe({
          next: () => {
            this.showMessage(`Test ${test.id} updated successfully`, 'success');
            this.loadTests();
          },
          error: (err) => {
            this.isLoading = false;
            this.showMessage(`Failed to update test: ${err.error?.error || err.message}`, 'error');
          }
        });
      }
    });
  }

  deleteTest(test: TestCase): void {
    const snackRef = this.snackBar.open(
      `Delete test ${test.id}?`,
      'CONFIRM',
      {
        duration: 5000,
        horizontalPosition: 'right',
        verticalPosition: 'top',
        panelClass: ['snackbar-warning']
      }
    );

    snackRef.onAction().subscribe(() => {
      this.isLoading = true;
      this.testService.deleteTestCase(test.file_name, test.id).subscribe({
        next: () => {
          this.showMessage(`Test ${test.id} deleted successfully`, 'success');
          this.loadTests();
        },
        error: (err) => {
          this.isLoading = false;
          this.showMessage(`Failed to delete test: ${err.error?.error || err.message}`, 'error');
        }
      });
    });
  }
  /**
 * Lance la génération du test par IA (Groq / Llama-3)
 */
generateTestWithAI(): void {
    if (!this.aiRequirement || this.aiRequirement.trim() === '') {
      this.showMessage('Please enter a functional requirement.', 'warning');
      return;
    }

    this.isGenerating = true;
    this.generatedCode = '';

    const defaultTestName = `TC-AI-${Date.now()}`;

    this.testService.generateTestWithAI(
      this.aiRequirement.trim(),
      defaultTestName,
      this.targetUrl?.trim() || undefined,
      this.testData?.trim() || undefined
    ).subscribe({
      next: (res) => {
        this.isGenerating = false;
        if (res && res.code) {
          this.generatedCode = res.code;
          this.aiProvider = res.provider || 'groq';
          this.showMessage(
            `Script generated successfully via ${(res.provider || 'groq').toUpperCase()}.`,
            'success'
          );
        } else {
          this.showMessage('Error: no code was generated by the AI.', 'error');
        }
      },
      error: (err) => {
        this.isGenerating = false;
        console.error('AI generation error:', err);
        const msg = err.error?.message || err.error?.error || 'AI generation failed.';
        this.showMessage(msg, 'error');
      }
    });
  }

/**
 * Enregistre le script généré dans le répertoire du projet et rafraîchit la liste des tests
 */

saveGeneratedTest(): void {
    if (!this.generatedCode) {
      return;
    }

    const fileName = `test_ai_${Date.now()}.robot`;

    this.testService.saveGeneratedTest(fileName, this.generatedCode).subscribe({
      next: () => {
        this.showMessage(`File ${fileName} saved successfully.`, 'success');
        this.generatedCode = '';
        this.aiRequirement = '';
        this.targetUrl = '';
        this.testData = '';
        this.loadTests();
      },
      error: (err) => {
        console.error('Save generated script error:', err);
        this.showMessage('Unable to save the test file.', 'error');
      }
    });
  }

  /** Clear AI generator form without saving. */
  clearAiGenerator(): void {
    this.aiRequirement = '';
    this.targetUrl = '';
    this.testData = '';
    this.generatedCode = '';
  }
}