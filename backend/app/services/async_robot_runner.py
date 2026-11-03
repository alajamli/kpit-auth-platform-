"""
Async Robot Framework Runner.

Ce module lance Robot Framework en arrière-plan et permet
de suivre la progression en temps réel via polling et d'annuler les processus.
"""
import subprocess
import threading
import uuid
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class AsyncRobotRunner:
    """
    Exécute Robot Framework de manière asynchrone.
    Permet le suivi en temps réel via un job_id et l'annulation.
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.robot_tests_dir = self.project_root / 'robot_tests'
        self.suites_dir = self.robot_tests_dir / 'suites'
        self.results_dir = self.robot_tests_dir / 'results'
        
        if sys.platform == "win32":
            self.venv_python = self.robot_tests_dir / 'venv' / 'Scripts' / 'python.exe'
        else:
            self.venv_python = self.robot_tests_dir / 'venv' / 'bin' / 'python'
            
        self.jobs: Dict[str, Dict] = {}
        self.processes: Dict[str, subprocess.Popen] = {}  # Pour garder la trace des processus à annuler
        self.jobs_lock = threading.Lock()
        
    def start_job(self, test_names: Optional[List[str]] = None, suite_file: Optional[str] = None, include_tags: Optional[List[str]] = None, exclude_tags: Optional[List[str]] = None) -> str:
        job_id = str(uuid.uuid4())
        
        with self.jobs_lock:
            self.jobs[job_id] = {
                'id': job_id,
                'status': 'starting',
                'started_at': datetime.now().isoformat(),
                'ended_at': None,
                'total': 0,
                'completed': 0,
                'passed': 0,
                'failed': 0,
                'current_test': None,
                'tests': [],
                'logs': [],
                'error': None,
                'report_available': False
            }
        
        thread = threading.Thread(
            target=self._run_robot,
            args=(job_id, test_names, suite_file, include_tags, exclude_tags),
            daemon=True
        )
        thread.start()
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        with self.jobs_lock:
            return self.jobs.get(job_id)
            
    def cancel_job(self, job_id: str) -> bool:
        """Annule un job en tuant l'arbre de processus natif (Chrome inclus)."""
        process = None

        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if not job or job.get('status') not in ('starting', 'running'):
                return False
                
            process = self.processes.get(job_id)
            
            # Mise à jour de l'UI
            job['status'] = 'failed'
            job['error'] = 'Execution cancelled by user'
            job['ended_at'] = datetime.now().isoformat()
            job['current_test'] = None
            self._add_log_direct(job, '⚠️ TEST EXECUTION CANCELLED BY USER')

        if process is not None:
            try:
                self._terminate_process_tree(process)
            except Exception as exc:
                with self.jobs_lock:
                    job = self.jobs.get(job_id)
                    if job:
                        self._add_log_direct(job, f'Cancel warning: {exc}')

        with self.jobs_lock:
            self.processes.pop(job_id, None)

        return True

    def _terminate_process_tree(self, process: subprocess.Popen) -> None:
        """Méthode native pour tuer Robot et le navigateur sans dépendance externe."""
        if process.poll() is not None:
            return
            
        pid = process.pid
        if sys.platform == 'win32':
            # /F = force, /T = kill process tree
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], capture_output=True, check=False)
        else:
            try:
                import signal
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except Exception:
                process.kill()
    
    def _run_robot(self, job_id: str, test_names=None, suite_file=None, include_tags=None, exclude_tags=None):
        try:
            self._update_job(job_id, {'status': 'running'})
            self._add_log(job_id, 'Initializing Robot Framework...')
            
            expected_total = self._compute_expected_total(test_names, suite_file, include_tags, exclude_tags)
            self._update_job(job_id, {'total': expected_total})
            self._add_log(job_id, f'Found {expected_total} test case(s) to run')

            cmd = self._build_command(test_names, suite_file, include_tags, exclude_tags)
            self._add_log(job_id, 'Starting test execution...')
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.robot_tests_dir),
                bufsize=1,
                universal_newlines=True
            )
            
            # Stocker pour l'annulation
            with self.jobs_lock:
                self.processes[job_id] = process
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    self._parse_line(job_id, line)
            
            process.wait(timeout=300)
            
            with self.jobs_lock:
                job = self.jobs.get(job_id)
                if job and job['status'] != 'failed': # Si pas annulé
                    if job['completed'] > 0 and job['total'] != job['completed']:
                        job['total'] = job['completed']
                    job['status'] = 'completed'
                    job['ended_at'] = datetime.now().isoformat()
                    job['report_available'] = (self.results_dir / 'report.html').exists()
                    self._add_log_direct(job, f"✅ Tests completed: {job['passed']}/{job['total']} passed")
            
        except subprocess.TimeoutExpired:
            self._update_job(job_id, {
                'status': 'failed', 'error': 'Test execution timed out (5 minutes)', 'ended_at': datetime.now().isoformat()
            })
        except Exception as e:
            self._update_job(job_id, {
                'status': 'failed', 'error': str(e), 'ended_at': datetime.now().isoformat()
            })
        finally:
            with self.jobs_lock:
                self.processes.pop(job_id, None)

    def _parse_line(self, job_id: str, line: str):
        """Parse la sortie de Robot Framework en temps réel pour mettre à jour l'overlay."""
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if not job or job.get('status') == 'failed':
                return
            
            if not line or line.startswith('==') or line.startswith('--'):
                return
            if 'DevTools' in line or 'ERROR:' in line or 'Created TensorFlow' in line:
                return
            
            is_pass = '| PASS |' in line
            is_fail = '| FAIL |' in line
            
            if is_pass or is_fail:
                parts = line.split('|')
                test_part = parts[0].strip().rstrip('. ').strip()
                
                # RECHERCHE DE 'TC-' N'IMPORTE OÙ DANS LE NOM (Aide à ignorer le nom de la suite)
                if 'TC-' not in test_part:
                    return
                
                # Extraire le nom à partir de 'TC-'
                tc_index = test_part.find('TC-')
                short_name = test_part[tc_index:].split('::')[0].strip().rstrip('. ').strip()
                
                # Éviter les doublons de comptage
                if any(t['name'] == short_name for t in job['tests']):
                    return
                
                status = 'PASS' if is_pass else 'FAIL'
                
                job['completed'] += 1
                if status == 'PASS':
                    job['passed'] += 1
                else:
                    job['failed'] += 1
                
                job['tests'].append({'name': short_name, 'status': status})
                icon = '✅' if status == 'PASS' else '❌'
                self._add_log_direct(job, f"{icon} {status}: {short_name}")
                job['current_test'] = None
                return
            
            # Détecter le début d'un test pour afficher le sous-titre "Running..."
            stripped = line.strip()
            if 'TC-' in stripped and '|' not in stripped:
                tc_index = stripped.find('TC-')
                test_name = stripped[tc_index:].split('::')[0].strip().rstrip('. ').strip()
                if test_name:
                    job['current_test'] = test_name

        

    def _compute_expected_total(self, test_names=None, suite_file=None, include_tags=None, exclude_tags=None) -> int:
        if test_names: return len(test_names)
        try:
            from app.services.robot_parser import get_default_parser
            parser = get_default_parser()
            tests = parser.get_all_test_cases()
            if suite_file: tests = [t for t in tests if t.get('file_name') == suite_file]
            if include_tags: tests = [t for t in tests if any(tag in t.get('tags', []) for tag in include_tags)]
            if exclude_tags: tests = [t for t in tests if not any(tag in t.get('tags', []) for tag in exclude_tags)]
            return len(tests)
        except Exception:
            return 0             
        
    def _build_command(self, test_names=None, suite_file=None, include_tags=None, exclude_tags=None) -> List[str]:
        cmd = [str(self.venv_python), '-m', 'robot', '-d', str(self.results_dir)]
        if test_names:
            for test_name in test_names: cmd.extend(['--test', test_name])
        if include_tags:
            for tag in include_tags: cmd.extend(['--include', tag])
        if exclude_tags:
            for tag in exclude_tags: cmd.extend(['--exclude', tag])
        if suite_file: cmd.append(str(self.suites_dir / suite_file))
        else: cmd.append(str(self.suites_dir))
        return cmd
    
    def _update_job(self, job_id: str, updates: Dict):
        with self.jobs_lock:
            if job_id in self.jobs: self.jobs[job_id].update(updates)
    
    def _add_log(self, job_id: str, message: str):
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if job: self._add_log_direct(job, message)
    
    def _add_log_direct(self, job: Dict, message: str):
        timestamp = datetime.now().strftime('%H:%M:%S')
        job['logs'].append({'timestamp': timestamp, 'message': message})
        if len(job['logs']) > 100: job['logs'] = job['logs'][-100:]


_runner_instance: Optional[AsyncRobotRunner] = None

def get_async_runner() -> AsyncRobotRunner:
    global _runner_instance
    if _runner_instance is None:
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
        _runner_instance = AsyncRobotRunner(project_root)
    return _runner_instance