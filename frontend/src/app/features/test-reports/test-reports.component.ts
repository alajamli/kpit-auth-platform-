import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TestManagementService } from '../../core/services/test-management.service';

@Component({
  selector: 'app-test-reports',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule
  ],
  templateUrl: './test-reports.component.html',
  styleUrl: './test-reports.component.scss'
})
export class TestReportsComponent implements OnInit {
  loading = false;
  reports: any[] = [];
  displayedColumns = ['folder', 'name', 'size_kb', 'modified_at', 'actions'];

  constructor(
    private testService: TestManagementService,
    private snackBar: MatSnackBar,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.loadReports();
  }

  loadReports(): void {
    this.loading = true;
    this.testService.getTestReports().subscribe({
      next: (res: any) => {
        this.loading = false;
        this.reports = res?.reports || [];
      },
      error: () => {
        this.loading = false;
        this.snackBar.open('Failed to load test reports from server', 'Close', { duration: 3000 });
      }
    });
  }

  /**
   * Télécharge le fichier en tant que Blob via HTTP (pour inclure le token JWT),
   * puis force le téléchargement côté navigateur.
   */
  downloadReport(row: any, fileType: 'report' | 'log' = 'report'): void {
    const fileName = fileType === 'log' ? 'log.html' : 'report.html';
    const url = this.testService.getReportFileUrl(row.folder, fileName);

    this.snackBar.open(`Downloading ${fileName}...`, '', { duration: 2000 });

    this.http.get(url, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const objectUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = objectUrl;
        // Format du nom de fichier : jobID_report.html
        a.download = `${row.folder === 'latest' ? 'root' : row.folder}_${fileName}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(objectUrl);
        
        this.snackBar.open(`${fileName} downloaded successfully!`, 'Close', { duration: 3000 });
      },
      error: () => {
        this.snackBar.open(`Failed to download ${fileName}`, 'Close', { duration: 3000 });
      }
    });
  }
  downloadPdf(row: any): void {
  const folder = row.folder || 'latest';
  const url = this.testService.getReportPdfUrl(folder);

  this.snackBar.open('Generating professional PDF report...', '', { duration: 2000 });

  this.http.get(url, { responseType: 'blob' }).subscribe({
    next: (blob) => {
      // Si le backend renvoie du JSON d'erreur avec content-type json
      if (blob.type && blob.type.includes('application/json')) {
        this.snackBar.open('PDF generation failed (see server logs)', 'Close', { duration: 4000 });
        return;
      }
      const objectUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = `KPIT_Test_Report_${folder === 'latest' ? 'latest' : folder}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(objectUrl);
      this.snackBar.open('PDF report downloaded successfully', 'Close', { duration: 3000 });
    },
    error: () => {
      this.snackBar.open('Failed to generate PDF. Ensure output.xml exists for this run.', 'Close', {
        duration: 4500
      });
    }
  });
}
}