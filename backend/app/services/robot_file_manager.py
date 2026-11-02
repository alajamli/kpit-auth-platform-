"""
Robot File Manager.

Ce module gère l'écriture, la modification et la suppression
directement dans les fichiers .robot physiques.
"""
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from app.services.robot_parser import get_default_parser

class RobotFileManager:
    
    def __init__(self, suites_directory: str):
        self.suites_dir = Path(suites_directory)
        # Création automatique et sécurisée du dossier des suites s'il n'existe pas
        os.makedirs(self.suites_dir, exist_ok=True)
    
    def _create_backup(self, file_path: str):
        """Crée une copie de sécurité avant modification."""
        if os.path.exists(file_path):
            backup_path = f"{file_path}.bak"
            shutil.copy2(file_path, backup_path)
            
    def _generate_new_id(self, suite_name: str) -> str:
        """Génère un nouvel ID (ex: TC-901) basé sur l'existant."""
        parser = get_default_parser()
        file_path = os.path.join(self.suites_dir, suite_name)
        tests = parser.parse_file(file_path) if os.path.exists(file_path) else []
        
        max_num = 900  # Les tests custom commencent à 900
        for t in tests:
            if t['id'].startswith('TC-'):
                try:
                    num = int(t['id'].replace('TC-', ''))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
                    
        return f"TC-{max_num + 1}"

    def add_test_case(self, suite_name: str, data: Dict) -> Tuple[bool, str, Dict]:
        """Ajoute un nouveau test à un fichier .robot (crée le fichier s'il n'existe pas)."""
        # S'assurer que le nom du fichier finit par .robot
        if not suite_name.endswith('.robot'):
            suite_name = f"{suite_name}.robot"

        file_path = self.suites_dir / suite_name
        
        # S'assurer que le dossier parent existe
        os.makedirs(file_path.parent, exist_ok=True)
        
        # Si le fichier n'existe pas, créer la structure initiale du fichier .robot
        if not file_path.exists():
            initial_headers = (
                "*** Settings ***\n"
                "Documentation    Test Suite for Automated Authentication & UI Testing\n"
                "Library          SeleniumLibrary\n\n"
                "*** Variables ***\n"
                "${BROWSER}       headlesschrome\n\n"
                "*** Test Cases ***\n"
            )
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(initial_headers)
        else:
            self._create_backup(str(file_path))
        
        test_id = self._generate_new_id(suite_name)
        test_name = data.get('name', 'Untitled Test')
        doc = data.get('documentation', 'Auto-generated test case.')
        tags = data.get('tags', ['custom'])
        
        tags_str = '    '.join(tags)
        
        # Si du code généré complet est fourni (comme le script IA)
        generated_code = data.get('code') or data.get('raw_code')
        
        if generated_code and '*** Test Cases ***' in generated_code:
            # Écrire directement le script IA généré dans le fichier
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(generated_code)
        else:
            # Sinon ajouter le bloc de test individuel
            new_test_block = f"\n\n{test_id} {test_name}\n"
            new_test_block += f"    [Documentation]    {doc}\n"
            if tags:
                new_test_block += f"    [Tags]             {tags_str}\n"
            
            steps = data.get('steps')
            if steps:
                new_test_block += f"{steps}\n"
            else:
                new_test_block += "    Log    ✅ Auto-generated test execution\n"
                new_test_block += "    Sleep    1s\n"
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(new_test_block)
            
        return True, "Test created successfully", {
            "id": test_id,
            "name": f"{test_id} {test_name}",
            "file_name": suite_name
        }

    def delete_test_case(self, suite_name: str, test_id: str) -> Tuple[bool, str]:
        """Supprime un test complet d'un fichier .robot via Regex."""
        file_path = self.suites_dir / suite_name
        
        if not file_path.exists():
            return False, f"File {suite_name} not found"
            
        self._create_backup(str(file_path))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        pattern = re.compile(rf"^{test_id}.*?(?=\n\S|\Z)", re.MULTILINE | re.DOTALL)
        
        if not pattern.search(content):
            return False, f"Test {test_id} not found in {suite_name}"
            
        new_content = pattern.sub("", content)
        new_content = re.sub(r'\n{3,}', '\n\n', new_content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return True, "Test deleted successfully"

    def update_test_case(self, suite_name: str, test_id: str, data: Dict) -> Tuple[bool, str]:
        """Modifie un test en le supprimant puis en le recréant à sa place."""
        file_path = self.suites_dir / suite_name
        
        if not file_path.exists():
            return False, f"File {suite_name} not found"
            
        self._create_backup(str(file_path))
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        pattern = re.compile(rf"^{test_id}.*?(?=\n\S|\Z)", re.MULTILINE | re.DOTALL)
        match = pattern.search(content)
        
        if not match:
            return False, f"Test {test_id} not found"
            
        old_block = match.group(0)
        
        steps_match = re.search(r'(?:\[Tags\].*?\n|\[Documentation\].*?\n)+(.*)', old_block, re.DOTALL)
        steps_content = steps_match.group(1) if steps_match else "\n    Log    No steps found"
        
        old_name = old_block.split('\n')[0].replace(test_id, '').strip()
        new_name = data.get('name', old_name)
        new_doc = data.get('documentation', 'Updated test case.')
        new_tags = data.get('tags', ['custom'])
        tags_str = '    '.join(new_tags)
        
        new_test_block = f"{test_id} {new_name}\n"
        new_test_block += f"    [Documentation]    {new_doc}\n"
        if new_tags:
            new_test_block += f"    [Tags]             {tags_str}\n"
        new_test_block += steps_content
        
        new_content = content.replace(old_block, new_test_block)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return True, "Test updated successfully"


def get_file_manager() -> RobotFileManager:
    """Détecte dynamiquement le dossier des suites de tests Robot Framework."""
    # 1. Mode Docker (Dossier racine /app/robot_tests/suites)
    docker_path = Path('/app/robot_tests/suites')
    if docker_path.parent.exists():
        suites_path = str(docker_path)
    else:
        # 2. Mode local de secours
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        root = current_dir
        while root.parent != root:
            if (root / 'robot_tests').exists() or (root / 'requirements.txt').exists():
                break
            root = root.parent
        suites_path = str(root / 'robot_tests' / 'suites')
    
    return RobotFileManager(suites_path)