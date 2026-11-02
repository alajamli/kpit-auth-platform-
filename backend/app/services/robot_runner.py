"""
Robot Framework Runner.

Ce module exécute les tests Robot Framework via subprocess
et retourne les résultats.
"""
import subprocess
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional


class RobotFrameworkRunner:
    """
    Exécute des tests Robot Framework et retourne les résultats.
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.robot_tests_dir = self.project_root / 'robot_tests'
        self.suites_dir = self.robot_tests_dir / 'suites'
        self.results_dir = self.robot_tests_dir / 'results'
        
        # S'assurer que les dossiers requis existent
        self.suites_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Détection dynamique : VENV si présent, sinon Python système (Docker)
        if sys.platform == "win32":
            candidate = self.robot_tests_dir / 'venv' / 'Scripts' / 'python.exe'
        else:
            candidate = self.robot_tests_dir / 'venv' / 'bin' / 'python'
            
        if candidate.exists():
            self.venv_python = candidate
        else:
            self.venv_python = Path(sys.executable)
    
    def run_tests(
        self,
        test_names: Optional[List[str]] = None,
        suite_file: Optional[str] = None,
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None
    ) -> Dict:
        cmd = self._build_command(
            test_names=test_names,
            suite_file=suite_file,
            include_tags=include_tags,
            exclude_tags=exclude_tags
        )
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.robot_tests_dir),
                timeout=300
            )
            return self._parse_result(result)
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test execution timed out (5 minutes limit)",
                "total": 0,
                "passed": 0,
                "failed": 0,
                "tests": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total": 0,
                "passed": 0,
                "failed": 0,
                "tests": []
            }
    
    def _build_command(
        self,
        test_names: Optional[List[str]] = None,
        suite_file: Optional[str] = None,
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None
    ) -> List[str]:
        cmd = [
            str(self.venv_python),
            '-m', 'robot',
            '-d', str(self.results_dir)
        ]
        
        if test_names:
            for test_name in test_names:
                cmd.extend(['--test', test_name])
        
        if include_tags:
            for tag in include_tags:
                cmd.extend(['--include', tag])
        
        if exclude_tags:
            for tag in exclude_tags:
                cmd.extend(['--exclude', tag])
        
        if suite_file:
            cmd.append(str(self.suites_dir / suite_file))
        else:
            cmd.append(str(self.suites_dir))
        
        return cmd
    
    def _parse_result(self, result: subprocess.CompletedProcess) -> Dict:
        output = result.stdout + result.stderr
        
        total = 0
        passed = 0
        failed = 0
        
        for line in output.split('\n'):
            line = line.strip()
            if 'passed' in line.lower() and 'failed' in line.lower():
                parts = line.split(',')
                for part in parts:
                    part = part.strip().lower()
                    if 'passed' in part:
                        try:
                            passed = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif 'failed' in part:
                        try:
                            failed = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
                    elif 'test' in part:
                        try:
                            total = int(part.split()[0])
                        except (ValueError, IndexError):
                            pass
        
        if total == 0:
            total = passed + failed
        
        test_results = self._extract_individual_results(output)
        
        return {
            "success": failed == 0 and total > 0,
            "total": total,
            "passed": passed,
            "failed": failed,
            "return_code": result.returncode,
            "tests": test_results,
            "output": output[-2000:] if len(output) > 2000 else output,
            "report_available": (self.results_dir / 'report.html').exists()
        }
    
    def _extract_individual_results(self, output: str) -> List[Dict]:
        test_results = []
        for line in output.split('\n'):
            line = line.strip()
            if '| PASS |' in line or '| FAIL |' in line:
                status = 'PASS' if '| PASS |' in line else 'FAIL'
                test_part = line.split('|')[0].strip()
                test_name = test_part.rstrip('. ')
                if test_name and not test_name.startswith('-'):
                    test_results.append({
                        "name": test_name,
                        "status": status
                    })
        return test_results
    
    def get_report_path(self) -> Optional[str]:
        report_path = self.results_dir / 'report.html'
        if report_path.exists():
            return str(report_path)
        return None


def get_default_runner() -> RobotFrameworkRunner:
    if os.path.exists('/app/robot_tests'):
        project_root = '/app'
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    
    return RobotFrameworkRunner(project_root)