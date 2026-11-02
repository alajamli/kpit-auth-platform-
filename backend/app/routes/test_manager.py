"""
Routes du Test Manager.

Layer 1 — SECURITY+ :
- AuthN : @jwt_required()
- AuthZ : @roles_required(...) selon la matrice admin / tester / viewer
"""
import os
from flask import request, send_from_directory, current_app
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required

from app.services.robot_parser import get_default_parser
from app.services.robot_runner import get_default_runner
from app.services.async_robot_runner import get_async_runner
from app.services.robot_file_manager import get_file_manager
from app.utils.decorators import roles_required
import logging

logger = logging.getLogger(__name__)
test_ns = Namespace(
    'tests',
    description='Test Management - List, Run and Manage Robot Framework tests'
)

run_request_model = test_ns.model('RunTestsRequest', {
    'test_names': fields.List(fields.String, description='Tests to run', example=['TC-001 ...']),
    'suite_file': fields.String(description='Suite file', example='02_auth_tests.robot'),
    'include_tags': fields.List(fields.String, example=['smoke']),
    'exclude_tags': fields.List(fields.String, example=['ui']),
})

test_case_model = test_ns.model('TestCaseRequest', {
    'name': fields.String(required=True, description='Test name'),
    'documentation': fields.String(description='Description'),
    'tags': fields.List(fields.String, description='Tags'),
})

# Modèles Swagger pour la génération LLM dynamique (Interne & Externe)
generate_test_model = test_ns.model('GenerateTest', {
    'requirement': fields.String(required=True, description='Functional requirement'),
    'test_name': fields.String(required=False, description='Test case name'),
    'target_suite': fields.String(required=False, description='Target .robot suite file'),
    'target_url': fields.String(required=False, description='External app/API URL'),
    'test_data': fields.String(required=False, description='Credentials or parameters'),
})

save_test_model = test_ns.model('SaveTestRequest', {
    'filename': fields.String(required=True, description='Nom du fichier (ex: test_login_ai.robot)'),
    'content': fields.String(required=True, description='Contenu Robot Framework')
})


def _results_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
    return os.path.join(project_root, 'robot_tests', 'results')


# ============================================
# LECTURE — admin, tester, viewer
# ============================================

@test_ns.route('/suites')
class TestSuitesList(Resource):
    @test_ns.doc('list_suites')
    @jwt_required()
    @roles_required('admin', 'tester', 'viewer')
    def get(self):
        try:
            suites = get_default_parser().get_all_suites()
            return {'success': True, 'count': len(suites), 'suites': suites}, 200
        except FileNotFoundError as e:
            return {'success': False, 'error': f'Suites directory not found: {str(e)}'}, 404
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@test_ns.route('/cases')
class TestCasesList(Resource):
    @test_ns.doc('list_test_cases')
    @jwt_required()
    @roles_required('admin', 'tester', 'viewer')
    def get(self):
        try:
            test_cases = get_default_parser().get_all_test_cases()
            total_tags = set()
            for tc in test_cases:
                total_tags.update(tc.get('tags', []))
            return {
                'success': True,
                'count': len(test_cases),
                'available_tags': sorted(list(total_tags)),
                'test_cases': test_cases,
            }, 200
        except FileNotFoundError as e:
            return {'success': False, 'error': str(e)}, 404
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@test_ns.route('/cases/<string:suite_name>')
class TestCasesBySuite(Resource):
    @test_ns.doc('list_test_cases_by_suite')
    @jwt_required()
    @roles_required('admin', 'tester', 'viewer')
    def get(self, suite_name):
        try:
            parser = get_default_parser()
            file_path = os.path.join(str(parser.suites_directory), suite_name)
            test_cases = parser.parse_file(file_path)
            return {
                'success': True,
                'suite': suite_name,
                'count': len(test_cases),
                'test_cases': test_cases,
            }, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


# ============================================
# EXÉCUTION — admin, tester
# ============================================

@test_ns.route('/run')
class RunTests(Resource):
    @test_ns.expect(run_request_model, validate=False)
    @test_ns.doc('run_tests')
    @jwt_required()
    @roles_required('admin', 'tester')
    def post(self):
        data = request.get_json() or {}
        try:
            result = get_default_runner().run_tests(
                test_names=data.get('test_names'),
                suite_file=data.get('suite_file'),
                include_tags=data.get('include_tags'),
                exclude_tags=data.get('exclude_tags'),
            )
            return result, (200 if result.get('success') else 207)
        except Exception as e:
            return {
                'success': False, 'error': str(e),
                'total': 0, 'passed': 0, 'failed': 0, 'tests': [],
            }, 500


@test_ns.route('/run/async')
class RunTestsAsync(Resource):
    @test_ns.expect(run_request_model, validate=False)
    @test_ns.doc('run_tests_async')
    @jwt_required()
    @roles_required('admin', 'tester')
    def post(self):
        data = request.get_json() or {}
        try:
            job_id = get_async_runner().start_job(
                test_names=data.get('test_names'),
                suite_file=data.get('suite_file'),
                include_tags=data.get('include_tags'),
                exclude_tags=data.get('exclude_tags'),
            )
            return {
                'success': True,
                'job_id': job_id,
                'message': 'Test execution started',
            }, 202
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@test_ns.route('/run/status/<string:job_id>')
class RunTestsStatus(Resource):
    @test_ns.doc('get_job_status')
    @jwt_required()
    @roles_required('admin', 'tester', 'viewer')
    def get(self, job_id):
        try:
            job = get_async_runner().get_job_status(job_id)
            if not job:
                return {'success': False, 'error': 'Job not found'}, 404
            return {'success': True, 'job': job}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@test_ns.route('/run/cancel/<string:job_id>')
class CancelTestsAsync(Resource):
    @test_ns.doc('cancel_job')
    @jwt_required()
    @roles_required('admin', 'tester')
    def post(self, job_id):
        try:
            success = get_async_runner().cancel_job(job_id)
            if success:
                return {'success': True, 'message': 'Job cancelled successfully'}, 200
            return {'success': False, 'error': 'Job not found or already finished'}, 404
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


# ============================================
# ENDPOINTS : RAPPORTS & LOGS ROBOT
# ============================================

@test_ns.route('/report')
@test_ns.route('/report.html')
class TestReport(Resource):
    """Servir le rapport synthétique HTML (report.html)."""
    
    @test_ns.doc('get_report')
    def get(self):
        results_dir = _results_dir()
        report_path = os.path.join(results_dir, 'report.html')
        
        if os.path.exists(report_path):
            return send_from_directory(results_dir, 'report.html', mimetype='text/html')
        else:
            return {
                'success': False,
                'error': 'No report available. Run tests first.'
            }, 404


@test_ns.route('/log')
@test_ns.route('/log.html')
class TestLogFile(Resource):
    """Servir le journal détaillé pas à pas (log.html)."""
    
    @test_ns.doc('get_log')
    def get(self):
        results_dir = _results_dir()
        log_path = os.path.join(results_dir, 'log.html')
        
        if os.path.exists(log_path):
            return send_from_directory(results_dir, 'log.html', mimetype='text/html')
        else:
            return {
                'success': False,
                'error': 'No log file available. Run tests first.'
            }, 404


@test_ns.route('/artifacts/<string:filename>')
@test_ns.route('/<string:filename>.png')
class TestArtifacts(Resource):
    """Servir les fichiers de preuves et screenshots."""
    
    @test_ns.doc('get_artifact')
    def get(self, filename):
        if '..' in filename or filename.startswith('/'):
            return {'success': False, 'error': 'Invalid filename'}, 400
            
        results_dir = _results_dir()
        target_file = filename if '.' in filename else f"{filename}.png"
        file_path = os.path.join(results_dir, target_file)
        
        if os.path.exists(file_path):
            return send_from_directory(results_dir, target_file)
        else:
            return {'success': False, 'error': f'File {target_file} not found'}, 404


# ============================================
# CRUD .robot — admin only
# ============================================

@test_ns.route('/suites/<string:suite_name>/cases')
class TestCaseAdd(Resource):
    @test_ns.expect(test_case_model)
    @test_ns.doc('add_test_case')
    @jwt_required()
    @roles_required('admin')
    def post(self, suite_name):
        data = request.get_json() or {}
        success, message, new_test = get_file_manager().add_test_case(suite_name, data)
        if success:
            return {'success': True, 'message': message, 'test': new_test}, 201
        return {'success': False, 'error': message}, 400


@test_ns.route('/suites/<string:suite_name>/cases/<string:test_id>')
class TestCaseManage(Resource):
    @test_ns.expect(test_case_model)
    @test_ns.doc('update_test_case')
    @jwt_required()
    @roles_required('admin')
    def put(self, suite_name, test_id):
        data = request.get_json() or {}
        success, message = get_file_manager().update_test_case(suite_name, test_id, data)
        if success:
            return {'success': True, 'message': message}, 200
        return {'success': False, 'error': message}, 404

    @test_ns.doc('delete_test_case')
    @jwt_required()
    @roles_required('admin')
    def delete(self, suite_name, test_id):
        success, message = get_file_manager().delete_test_case(suite_name, test_id)
        if success:
            return {'success': True, 'message': message}, 200
        return {'success': False, 'error': message}, 404


# ============================================
# IA GENERATOR (Layer 3 LLM) — admin & tester
# ============================================

@test_ns.route('/generate')
class GenerateTestScript(Resource):
    @jwt_required()
    @roles_required('admin', 'tester')
    @test_ns.expect(generate_test_model)
    @test_ns.doc(security='Bearer')
    def post(self):
        """
        [Layer 3 - AI] Génère un script de test Robot Framework via LLM
        (Suite interne KPIT ou Cible Client Externe).
        """
        data = request.get_json() or {}
        requirement = (data.get('requirement') or '').strip()
        test_name = (data.get('test_name') or 'TC-AI Generated Test').strip()
        target_suite = (data.get('target_suite') or '03_ui_tests.robot').strip()
        target_url = (data.get('target_url') or '').strip()
        test_data = (data.get('test_data') or '').strip()
        
        if not requirement:
            return {'message': 'L\'exigence fonctionnelle est requise'}, 400
            
        try:
            from app.services.llm_service import LLMService
            result = LLMService.generate_robot_test(
                requirement=requirement,
                test_name=test_name,
                target_suite=target_suite,
                target_url=target_url or None,
                test_data=test_data or None
            )
            return result, 200
        except Exception as e:
            logger.exception("AI generation failed")
            return {'message': f'Erreur lors de la génération IA: {str(e)}'}, 500

@test_ns.route('/save-generated')
class SaveGeneratedTestScript(Resource):
    @jwt_required()
    @roles_required('admin', 'tester')
    @test_ns.expect(save_test_model)
    @test_ns.doc(security='Bearer')
    def post(self):
        """
        [Layer 3 - AI] Enregistre ou fusionne un script généré dans la suite sélectionnée
        """
        data = request.get_json() or {}
        filename = data.get('filename', '').strip()
        content = data.get('content', '').strip()
        
        if not filename or not content:
            return {'message': 'Le nom de fichier et le contenu sont requis'}, 400
            
        safe_filename = os.path.basename(filename)
        if not safe_filename.endswith('.robot'):
            safe_filename += '.robot'
            
        try:
            parser = get_default_parser()
            suites_dir = str(parser.suites_directory)
            os.makedirs(suites_dir, exist_ok=True)
            file_path = os.path.join(suites_dir, safe_filename)
            
            if os.path.exists(file_path):
                import re
                test_case_match = re.search(r'\*\*\* Test Cases \*\*\*\s*(.*)', content, re.DOTALL)
                test_case_body = test_case_match.group(1).strip() if test_case_match else content
                
                with open(file_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n\n{test_case_body}\n")
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
            return {
                'message': f'Test enregistré dans {safe_filename}', 
                'file_path': file_path,
                'file_name': safe_filename
            }, 201
        except Exception as e:
            return {'message': f'Erreur d\'écriture fichier: {str(e)}'}, 500