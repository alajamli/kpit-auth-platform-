import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { switchMap, takeWhile, catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
export interface AIGenerateResponse {
  generated_code: string;
  code: string;
  provider: string;
}
import {
  SuitesResponse,
  TestCasesResponse,
  RunTestsRequest,
  RunTestsResponse,
  AsyncRunResponse,  
  JobStatusResponse,   
  TestCaseMutationResponse,
  TestCaseRequest
} from '../models/test.model';

import {  interval, of, throwError } from 'rxjs';

/**
 * Service pour la gestion des tests Robot Framework.
 * Communique avec le backend Flask (endpoints /api/tests/*)
 */
@Injectable({
  providedIn: 'root'
})
export class TestManagementService {
  
  private apiUrl = `${environment.apiUrl}/tests`;

  constructor(private http: HttpClient) {}

  addTestCase(suiteName: string, data: TestCaseRequest): Observable<TestCaseMutationResponse> {
    return this.http.post<TestCaseMutationResponse>(`${this.apiUrl}/suites/${suiteName}/cases`, data);
  }

  updateTestCase(suiteName: string, testId: string, data: TestCaseRequest): Observable<TestCaseMutationResponse> {
    return this.http.put<TestCaseMutationResponse>(`${this.apiUrl}/suites/${suiteName}/cases/${testId}`, data);
  }
  deleteTestCase(suiteName: string, testId: string): Observable<TestCaseMutationResponse> {
    return this.http.delete<TestCaseMutationResponse>(`${this.apiUrl}/suites/${suiteName}/cases/${testId}`);
  }


  /**
   * Récupérer la liste de toutes les suites (fichiers .robot).
   */
  getSuites(): Observable<SuitesResponse> {
    return this.http.get<SuitesResponse>(`${this.apiUrl}/suites`);
  }

  /**
   * Récupérer tous les test cases de toutes les suites.
   */
  getAllTestCases(): Observable<TestCasesResponse> {
    return this.http.get<TestCasesResponse>(`${this.apiUrl}/cases`);
  }

  /**
   * Récupérer les test cases d'une suite spécifique.
   */
  getTestCasesBySuite(suiteName: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/cases/${suiteName}`);
  }

  /**
   * Exécuter des tests.
   * 
   * @param request - Paramètres d'exécution (tests, tags, suite)
   */
  runTestsAsync(request: RunTestsRequest = {}): Observable<AsyncRunResponse> {
  return this.http.post<AsyncRunResponse>(`${this.apiUrl}/run/async`, request);
}

/**
 * Récupère l'état actuel d'un job.
 */
getJobStatus(jobId: string): Observable<JobStatusResponse> {
  return this.http.get<JobStatusResponse>(`${this.apiUrl}/run/status/${jobId}`);
}

/**
 * Fait du polling sur un job jusqu'à ce qu'il soit terminé.
 * Émet le statut à chaque poll (toutes les 500ms).
 */
pollJobStatus(jobId: string, intervalMs: number = 500): Observable<JobStatusResponse> {
  return interval(intervalMs).pipe(
    switchMap(() => this.getJobStatus(jobId)),
    takeWhile(response => 
      response.job.status === 'starting' || response.job.status === 'running',
      true // inclusive : émet aussi la dernière valeur (completed/failed)
    ),
    catchError(error => {
      console.error('Polling error:', error);
      return throwError(() => error);
    })
  );
}
cancelJob(jobId: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/run/cancel/${jobId}`, {});
  }

  generateTestWithAI(
    requirement: string,
    testName: string,
    targetUrl?: string,
    testData?: string,
    targetSuite?: string
  ): Observable<any> {
    const body: Record<string, any> = {
      requirement,
      test_name: testName
    };

    if (targetUrl) body['target_url'] = targetUrl;
    if (testData) body['test_data'] = testData;
    if (targetSuite) body['target_suite'] = targetSuite;

    return this.http.post<any>(`${this.apiUrl}/generate`, body);
  } 

saveGeneratedTest(filename: string, content: string): Observable<{ message: string; file_path: string }> {
  return this.http.post<{ message: string; file_path: string }>(
    `${this.apiUrl}/save-generated`,
    { filename, content }
  );
}
getTestHistory(): Observable<any> {
  return this.http.get(`${this.apiUrl}/history`);
}

getTestHistoryDetail(jobId: string): Observable<any> {
  return this.http.get(`${this.apiUrl}/history/${jobId}`);
}

getTestReports(): Observable<any> {
  return this.http.get(`${this.apiUrl}/reports`);
}

getReportFileUrl(folder: string, fileName: string = 'report.html'): string {
  const sub = folder === 'latest' ? fileName : `${folder}/${fileName}`;
  return `${this.apiUrl}/reports/file/${sub}`;
}
getReportPdfUrl(folder: string): string {
  return `${this.apiUrl}/reports/pdf/${encodeURIComponent(folder)}`;
}

}