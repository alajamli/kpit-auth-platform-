"""
Services Package Initialization.

Ce paquet réunit l'ensemble des services métiers du backend avec leurs noms exacts :
- AnomalyDetectorService (Isolation Forest AI)
- AsyncRobotRunner & RobotFrameworkRunner (Exécution Robot Framework)
- log_audit_event (Logs d'audit de sécurité)
- EmailService (Envoi d'OTP via Brevo)
- LLMService (Génération AI via Groq)
- RobotFileManager (Gestion des fichiers .robot)
- RobotFrameworkParser (Analyse des scripts .robot)
"""

from app.services.anomaly_detector import AnomalyDetectorService
from app.services.async_robot_runner import AsyncRobotRunner
from app.services.audit_service import log_audit_event
from app.services.email_service import EmailService
from app.services.llm_service import LLMService
from app.services.robot_file_manager import RobotFileManager
from app.services.robot_parser import RobotFrameworkParser
from app.services.robot_runner import RobotFrameworkRunner

# Singletons / Instances pour les routes qui importent des instances
try:
    anomaly_detector = AnomalyDetectorService()
except Exception:
    anomaly_detector = AnomalyDetectorService

try:
    email_service = EmailService()
except Exception:
    email_service = EmailService

try:
    llm_service = LLMService()
except Exception:
    llm_service = LLMService

# Aliases de compatibilité pour les routes
audit_service = log_audit_event
RobotRunner = RobotFrameworkRunner
RobotParser = RobotFrameworkParser

__all__ = [
    'AnomalyDetectorService',
    'anomaly_detector',
    'AsyncRobotRunner',
    'log_audit_event',
    'audit_service',
    'EmailService',
    'email_service',
    'LLMService',
    'llm_service',
    'RobotFileManager',
    'RobotFrameworkParser',
    'RobotParser',
    'RobotFrameworkRunner',
    'RobotRunner'
]