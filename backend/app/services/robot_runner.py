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
        """
        Initialise le runner.
        
        Args:
            project_root: Chemin racine du projet
        """
        self.project_root = Path(project_root)
        self.robot_tests_dir = self.project_root / 'robot_tests'
        self.suites_dir = self.robot_tests_dir / 'suites'
        self.results_dir = self.robot_tests_dir / 'results'
        
        # Détection dynamique du chemin du Python de l'environnement virtuel (Cross-platform)
        if sys.platform == "win32":
            self.venv_python = self.robot_tests_dir / 'venv' / 'Scripts' / 'python.exe'
        else:
            self.venv_python = self.robot_tests_dir / 'venv' / 'bin' / 'python'
        
        # Créer le dossier results s'il n'existe pas
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def run_tests(
        self,
        test_names: Optional[List[str]] = None,
        suite_file: Optional[str] = None,
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None
    ) -> Dict:
        # Le reste du fichier demeure identique...
        """
        Exécuter des tests Robot Framework.
        
        Args:
            test_names: Liste des noms de tests à exécuter (None = tous)
            suite_file: Fichier .robot spécifique (None = tous)
            include_tags: Tags à inclure
            exclude_tags: Tags à exclure
        
        Returns:
            Dict avec les résultats de l'exécution
        """
        # Construire la commande robot
        cmd = self._build_command(
            test_names=test_names,
            suite_file=suite_file,
            include_tags=include_tags,
            exclude_tags=exclude_tags
        )
        
        try:
            # Exécuter la commande
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.robot_tests_dir),
                timeout=300  # 5 minutes max
            )
            
            # Parser le résultat
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
        """
        Construit la commande robot à exécuter.
        
        Returns:
            List[str]: La commande sous forme de liste
        """
        cmd = [
            str(self.venv_python),
            '-m', 'robot',
            '-d', str(self.results_dir)
        ]
        
        # Ajouter les filtres par nom de test
        if test_names:
            for test_name in test_names:
                cmd.extend(['--test', test_name])
        
        # Ajouter les filtres par tag
        if include_tags:
            for tag in include_tags:
                cmd.extend(['--include', tag])
        
        if exclude_tags:
            for tag in exclude_tags:
                cmd.extend(['--exclude', tag])
        
        # Ajouter le fichier/dossier cible
        if suite_file:
            cmd.append(str(self.suites_dir / suite_file))
        else:
            cmd.append(str(self.suites_dir))
        
        return cmd
    
    def _parse_result(self, result: subprocess.CompletedProcess) -> Dict:
        """
        Parse le résultat de l'exécution Robot Framework.
        
        Args:
            result: Résultat de subprocess.run
        
        Returns:
            Dict avec les résultats structurés
        """
        output = result.stdout + result.stderr
        
        # Chercher les statistiques dans la sortie
        total = 0
        passed = 0
        failed = 0
        
        # Parser la ligne de résumé
        # Format : "X tests, Y passed, Z failed"
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
        
        # Si pas trouvé total, calculer
        if total == 0:
            total = passed + failed
        
        # Extraire les résultats individuels des tests
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
        """
        Extrait les résultats individuels de chaque test depuis la sortie.
        
        Returns:
            Liste des résultats par test
        """
        test_results = []
        
        for line in output.split('\n'):
            line = line.strip()
            
            # Chercher les lignes de résultat de test
            # Format : "TC-XXX Test Name ... | PASS |" ou "| FAIL |"
            if '| PASS |' in line or '| FAIL |' in line:
                # Nettoyer la ligne
                status = 'PASS' if '| PASS |' in line else 'FAIL'
                
                # Extraire le nom du test
                test_part = line.split('|')[0].strip()
                
                # Enlever les points de remplissage
                test_name = test_part.rstrip('. ')
                
                if test_name and not test_name.startswith('-'):
                    test_results.append({
                        "name": test_name,
                        "status": status
                    })
        
        return test_results
    
    def get_report_path(self) -> Optional[str]:
        """
        Retourne le chemin du rapport HTML s'il existe.
        """
        report_path = self.results_dir / 'report.html'
        if report_path.exists():
            return str(report_path)
        return None


def get_default_runner() -> RobotFrameworkRunner:
    """
    Retourne un runner configuré avec le chemin par défaut.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    
    return RobotFrameworkRunner(project_root)