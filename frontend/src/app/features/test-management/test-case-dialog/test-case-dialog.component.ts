import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogRef, MatDialogModule } from '@angular/material/dialog';

import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { TestManagementService } from '../../../core/services/test-management.service';

@Component({
  selector: 'app-test-case-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatIconModule,
    MatTabsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule
  ],
  templateUrl: './test-case-dialog.component.html',
  styleUrl: './test-case-dialog.component.scss'
})
export class TestCaseDialogComponent implements OnInit {
  isEditMode = false;

  /** Doit être bindé avec [(selectedIndex)] sur mat-tab-group */
  selectedTabIndex = 0;

  // Manual
  suiteName = '';
  testName = '';
  documentation = '';
  selectedTags: string[] = [];
  suites: string[] = [];
  availableTags: string[] = [];

  // AI Generator — Step 1.3 generalized (sync with main page)
  aiRequirement: string = '';
  aiTestName: string = 'TC-AI-01 Test Case';
  aiTargetSuite: string = '';
  customSuiteName: string = '';
  targetUrl: string = '';   // NEW
  testData: string = '';    // NEW
  generatedCode: string = '';
  aiProvider: string = 'groq';
  isGenerating: boolean = false;
  isSavingAI: boolean = false;

  constructor(
    public dialogRef: MatDialogRef<TestCaseDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: any,
    private testService: TestManagementService,
    private snackBar: MatSnackBar
  ) {}

  /** Testers may generate with AI but not create tests manually (server enforces it too). */
  aiOnly = false;

  ngOnInit(): void {
    this.isEditMode = this.data?.mode === 'edit';
    this.aiOnly = !!this.data?.aiOnly;
    if (!this.isEditMode && this.data?.initialTab === 'ai') this.selectedTabIndex = 1;
    this.suites = this.data?.suites || [];
    this.availableTags = this.data?.availableTags || [];
    this.suiteName = this.data?.suiteName || (this.suites.length ? this.suites[0] : '');

    // Initialisation de la suite cible pour la génération IA
    this.aiTargetSuite = this.suites.length ? this.suites[0] : 'NEW_SUITE';
    if (this.aiTargetSuite === 'NEW_SUITE') {
      this.customSuiteName = '03_ai_generated_tests.robot';
    }

    if (this.isEditMode && this.data?.testCase) {
      this.testName = this.data.testCase.name || '';
      this.documentation = this.data.testCase.documentation || '';
      this.selectedTags = [...(this.data.testCase.tags || [])];
      this.suiteName = this.data.testCase.file_name || this.suiteName;
    }
  }

  isValidManualForm(): boolean {
    return !!(this.testName && this.testName.trim() && this.suiteName);
  }

  onSaveManual(): void {
    if (!this.isValidManualForm()) return;
    this.dialogRef.close({
      type: 'manual',
      suiteName: this.suiteName,
      data: {
        name: this.testName.trim(),
        documentation: (this.documentation || '').trim(),
        tags: this.selectedTags
      }
    });
  }

    generateWithAI(): void {
  if (!this.aiRequirement?.trim()) {
    this.snackBar.open('Please enter a functional requirement.', 'Close', {
      duration: 3000,
      panelClass: ['snackbar-warning'],
      horizontalPosition: 'right',
      verticalPosition: 'top'
    });
    return;
  }

  if (this.aiTargetSuite === 'NEW_SUITE' && !this.customSuiteName?.trim()) {
    this.snackBar.open('Please enter a new suite filename.', 'Close', {
      duration: 3000,
      panelClass: ['snackbar-warning'],
      horizontalPosition: 'right',
      verticalPosition: 'top'
    });
    return;
  }

  if (!this.aiTestName?.trim()) {
    this.snackBar.open('Please enter a test case name / ID.', 'Close', {
      duration: 3000,
      panelClass: ['snackbar-warning'],
      horizontalPosition: 'right',
      verticalPosition: 'top'
    });
    return;
  
    }

    this.isGenerating = true;
    this.generatedCode = '';

    // Resolve suite: existing file OR custom new suite name
    const resolvedSuite =
      this.aiTargetSuite === 'NEW_SUITE'
        ? (this.customSuiteName?.trim() || 'ai_generated_tests.robot')
        : (this.aiTargetSuite || '03_ui_tests.robot');

    const testName = (this.aiTestName || `TC-AI-${Date.now()}`).trim();

    // Signature service (order matters):
    // requirement, testName, targetUrl?, testData?, targetSuite?
    this.testService
      .generateTestWithAI(
        this.aiRequirement.trim(),
        testName,
        this.targetUrl?.trim() || undefined,
        this.testData?.trim() || undefined,
        resolvedSuite
      )
      .subscribe({
        next: (res) => {
          this.isGenerating = false;
          this.generatedCode = res?.code || res?.generated_code || '';
          this.aiProvider = res?.provider || 'groq';

          if (this.generatedCode) {
            this.snackBar.open(
              `Script generated successfully (${(this.aiProvider || 'groq').toUpperCase()}).`,
              'Close',
              {
                duration: 3000,
                panelClass: ['snackbar-success'],
                horizontalPosition: 'right',
                verticalPosition: 'top'
              }
            );
          } else {
            this.snackBar.open('Error: no code was generated by the AI.', 'Close', {
              duration: 4000,
              panelClass: ['snackbar-error'],
              horizontalPosition: 'right',
              verticalPosition: 'top'
            });
          }
        },
        error: (err) => {
          this.isGenerating = false;
          console.error('AI generation error:', err);
          const msg =
            err?.error?.message || err?.error?.error || 'AI generation failed.';
          this.snackBar.open(msg, 'Close', {
            duration: 5000,
            panelClass: ['snackbar-error'],
            horizontalPosition: 'right',
            verticalPosition: 'top'
          });
        }
      });
  }

  onSaveAIGenerated(): void {
    if (!this.generatedCode || this.isSavingAI) return;

    this.isSavingAI = true;

    // Détermination du nom de fichier de suite de destination
    let targetFile = this.aiTargetSuite;
    if (this.aiTargetSuite === 'NEW_SUITE') {
      targetFile = (this.customSuiteName || '').trim() || '03_ai_generated_tests.robot';
    }
    if (!targetFile.endsWith('.robot')) {
      targetFile += '.robot';
    }

    this.testService.saveGeneratedTest(targetFile, this.generatedCode).subscribe({
      next: () => {
        this.isSavingAI = false;
        this.snackBar.open(`Saved to suite: ${targetFile}`, 'Close', {
          duration: 3500,
          panelClass: ['snackbar-success']
        });
        // Type ai_saved → le composant parent appelle loadTests()
        this.dialogRef.close({ type: 'ai_saved', filename: targetFile });
      },
      error: (err) => {
        this.isSavingAI = false;
        const msg = err?.error?.message || 'Failed to save generated script.';
        this.snackBar.open(msg, 'Close', {
          duration: 5000,
          panelClass: ['snackbar-error']
        });
      }
    });
  }

    clearAI(): void {
  this.aiRequirement = '';
  this.aiTestName = 'TC-AI-01 Test Case';
  this.targetUrl = '';
  this.testData = '';
  this.generatedCode = '';
  this.aiProvider = 'groq';
  this.isGenerating = false;
}

  copyCode(): void {
    if (!this.generatedCode) return;
    navigator.clipboard.writeText(this.generatedCode).then(() => {
      this.snackBar.open('Script copied to clipboard', 'Close', { duration: 2000 });
    });
  }
}