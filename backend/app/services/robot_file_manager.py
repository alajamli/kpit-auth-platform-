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
    
    def _create_backup(self, file_path: str):
        """Crée une copie de sécurité avant modification."""
        if os.path.exists(file_path):
            backup_path = f"{file_path}.bak"
            shutil.copy2(file_path, backup_path)
            
    def _generate_new_id(self, suite_name: str) -> str:
        """Génère un nouvel ID (ex: TC-901) basé sur l'existant."""
        parser = get_default_parser()
        file_path = os.path.join(self.suites_dir, suite_name)
        tests = parser.parse_file(file_path)
        
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
        """Ajoute un nouveau test à la fin du fichier .robot."""
        file_path = self.suites_dir / suite_name
        
        if not file_path.exists():
            return False, f"File {suite_name} not found", {}
            
        self._create_backup(str(file_path))
        
        test_id = self._generate_new_id(suite_name)
        test_name = data.get('name', 'Untitled Test')
        doc = data.get('documentation', 'Auto-generated test case.')
        tags = data.get('tags', ['custom'])
        
        # Formater les tags avec des espaces (ex: tag1    tag2)
        tags_str = '    '.join(tags)
        
        # Générer le bloc de code Robot Framework
        new_test_block = f"\n\n{test_id} {test_name}\n"
        new_test_block += f"    [Documentation]    {doc}\n"
        
        if tags:
            new_test_block += f"    [Tags]             {tags_str}\n"
            
        new_test_block += "    \n"
        new_test_block += "    # Auto-generated steps\n"
        new_test_block += "    Log    ✅ This is an auto-generated test case\n"
        new_test_block += "    Sleep    1s    reason=Simulate test execution\n"
        
        # Ajouter à la fin du fichier
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
            
        # Regex MAGIQUE : Trouve la ligne qui commence par l'ID, 
        # puis capture tout jusqu'à la prochaine ligne qui n'est pas indentée (prochain test) 
        # ou jusqu'à la fin du fichier.
        pattern = re.compile(rf"^{test_id}.*?(?=\n\S|\Z)", re.MULTILINE | re.DOTALL)
        
        if not pattern.search(content):
            return False, f"Test {test_id} not found in {suite_name}"
            
        # Remplacer le test par une chaîne vide
        new_content = pattern.sub("", content)
        
        # Nettoyer les espaces multiples vides
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
            
        # Trouver le bloc exact
        pattern = re.compile(rf"^{test_id}.*?(?=\n\S|\Z)", re.MULTILINE | re.DOTALL)
        match = pattern.search(content)
        
        if not match:
            return False, f"Test {test_id} not found"
            
        old_block = match.group(0)
        
        # --- MISE À JOUR SÉCURISÉE ---
        # On ne met à jour QUE la Doc et les Tags. 
        # On garde les étapes (steps) d'origine pour ne pas casser le test !
        
        # 1. Isoler les étapes (tout ce qui vient après les tags/docs)
        steps_match = re.search(r'(?:\[Tags\].*?\n|\[Documentation\].*?\n)+(.*)', old_block, re.DOTALL)
        steps_content = steps_match.group(1) if steps_match else "\n    Log    No steps found"
        
        # 2. Récupérer l'ancien nom si non fourni
        old_name = old_block.split('\n')[0].replace(test_id, '').strip()
        new_name = data.get('name', old_name)
        new_doc = data.get('documentation', 'Updated test case.')
        new_tags = data.get('tags', ['custom'])
        tags_str = '    '.join(new_tags)
        
        # 3. Construire le nouveau bloc
        new_test_block = f"{test_id} {new_name}\n"
        new_test_block += f"    [Documentation]    {new_doc}\n"
        if new_tags:
            new_test_block += f"    [Tags]             {tags_str}\n"
        new_test_block += steps_content
        
        # 4. Remplacer dans le contenu global
        new_content = content.replace(old_block, new_test_block)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return True, "Test updated successfully"


def get_file_manager() -> RobotFileManager:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    suites_path = os.path.join(project_root, 'robot_tests', 'suites')
    return RobotFileManager(suites_path)