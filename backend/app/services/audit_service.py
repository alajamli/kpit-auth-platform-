from app.extensions import db
from app.models.audit import AuditLog
from flask import request

def log_audit_event(event_type, login=None, user_id=None, details=None, is_success=True):
    """
    Service centralisé pour enregistrer les événements de sécurité (Audit Trail).
    """
    try:
        # Récupération automatique de l'IP et du User-Agent de la requête HTTP
        ip_address = request.remote_addr if request else '127.0.0.1'
        user_agent = request.headers.get('User-Agent', 'System') if request else 'System'
        
        audit_entry = AuditLog(
            event_type=event_type,
            login=login,
            user_id=user_id,
            details=details,
            is_success=is_success,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(audit_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[AUDIT LOG ERROR] Failed to record audit event: {str(e)}")