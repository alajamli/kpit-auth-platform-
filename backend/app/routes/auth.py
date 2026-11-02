"""
Routes d'authentification KPIT Auth Platform.

Layer 0 : register + login
Layer 1 : bcrypt + JWT + Rate Limiting + Audit Logs
Layer 2 : Intelligence Artificielle (Isolation Forest Anomaly Detection)
Layer 3 : Authentification Adaptative au Risque (Risk-Based 2FA / TOTP)
Layer 4 : Authentification OAuth2 / Google SSO (Auto-Provisioning)
"""
import os
import datetime
import base64
import json
import pyotp

from flask import request, current_app
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from app.extensions import db, limiter
from app.models import User
from app.models.audit import AuditLog

from app.services.anomaly_detector import anomaly_detector
from app.services.email_service import email_service
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


def log_audit_event(event_type, login=None, user_id=None, is_success=False):
    try:
        ip = request.remote_addr or '127.0.0.1'
        ua = request.headers.get('User-Agent', '')[:255]
        
        score, is_anomaly = anomaly_detector.evaluate_connection(
            login_attempted=login or 'unknown',
            ip_address=ip,
            is_success=is_success
        )
        
        log_entry = AuditLog(
            user_id=user_id,
            login_attempted=login,
            event=event_type,
            ip_address=ip,
            user_agent=ua,
            anomaly_score=score,
            is_anomaly=is_anomaly
        )
        db.session.add(log_entry)
        db.session.commit()
        
        return score, is_anomaly
    except Exception as e:
        db.session.rollback()
        print(f"[AUDIT/AI LOG ERROR] {e}")
        return 0.0, False


def mask_email(email: str) -> str:
    """Masque un email (ex: ahmed@kpit.com -> a***d@kpit.com)."""
    if not email or '@' not in email:
        return '***@***.com'
    parts = email.split('@')
    name = parts[0]
    domain = parts[1]
    masked_name = name[0] + '***' + name[-1] if len(name) > 2 else name[0] + '***'
    return f"{masked_name}@{domain}"


auth_ns = Namespace(
    'auth',
    description='Authentication endpoints with Risk-Based Adaptive 2FA & Google SSO'
)

register_model = auth_ns.model('RegisterRequest', {
    'first_name': fields.String(required=True, example='Ahmed'),
    'last_name': fields.String(required=True, example='Ben Ali'),
    'email': fields.String(required=True, example='ahmed@test.com'),
    'login': fields.String(required=True, example='ahmed'),
    'password': fields.String(required=True, example='ahmed123'),
    'role': fields.String(required=False, default='viewer', example='viewer')
})

login_model = auth_ns.model('LoginRequest', {
    'login': fields.String(required=True, example='ahmed'),
    'password': fields.String(required=True, example='ahmed123')
})

verify_2fa_model = auth_ns.model('Verify2FARequest', {
    'login': fields.String(required=True, description='Username', example='ahmed'),
    'otp_code': fields.String(required=True, description='6-digit 2FA OTP code', example='123456')
})

resend_2fa_model = auth_ns.model('Resend2FARequest', {
    'login': fields.String(required=True, description='Username', example='ahmed')
})

google_login_model = auth_ns.model('GoogleLoginModel', {
    'id_token': fields.String(required=True, description='Token ID transmis par Google Sign-In')
})


@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model, validate=False)
    @auth_ns.doc('register_user')
    def post(self):
        data = request.get_json() or {}

        required_fields = ['first_name', 'last_name', 'email', 'login', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return {'success': False, 'error': f'Missing or empty field: {field}'}, 400

        if len(str(data['password'])) < 6:
            return {'success': False, 'error': 'Password must be at least 6 characters'}, 400

        if User.query.filter_by(email=data['email']).first():
            return {'success': False, 'error': 'Email already registered'}, 409

        if User.query.filter_by(login=data['login']).first():
            return {'success': False, 'error': 'Login already taken'}, 409

        # On force le rôle à 'tester' pour toute inscription publique
        user_role = 'tester'

        new_user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            login=data['login'],
            role=user_role
        )
        new_user.set_password(data['password'])
        new_user.generate_otp_secret()

        try:
            db.session.add(new_user)
            db.session.commit()
            log_audit_event('REGISTER_SUCCESS', login=new_user.login, user_id=new_user.id, is_success=True)
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'Database error: {str(e)}'}, 500

        return {
            'success': True,
            'message': 'User created successfully',
            'user': new_user.to_dict()
        }, 201


@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model, validate=False)
    @auth_ns.doc('login_user')
    @limiter.limit("30 per minute")
    def post(self):
        data = request.get_json() or {}
        login_input = data.get('login')
        password_input = data.get('password')

        if not login_input or not password_input:
            score, is_anomaly = log_audit_event('LOGIN_INVALID_INPUT', login=login_input, is_success=False)
            return {'success': False, 'error': 'Login and password are required'}, 400

        user = User.query.filter_by(login=login_input).first()

        if not user or not user.check_password(password_input):
            score, is_anomaly = log_audit_event('LOGIN_FAILED', login=login_input, user_id=user.id if user else None, is_success=False)
            return {
                'success': False,
                'error': 'Invalid username or password',
                'anomaly_score': score,
                'is_anomaly': is_anomaly
            }, 401

        # Vérification du statut du compte (Désactivé par l'Admin)
        if not user.is_verified:
            score, is_anomaly = log_audit_event('LOGIN_BLOCKED_DISABLED', login=login_input, user_id=user.id, is_success=False)
            return {
                'success': False,
                'error': 'Your account has been disabled by an administrator',
                'anomaly_score': score,
                'is_anomaly': is_anomaly
            }, 403

        score, is_anomaly = log_audit_event('LOGIN_SUCCESS', login=login_input, user_id=user.id, is_success=True)

        if not user.otp_secret:
            user.generate_otp_secret()
            db.session.commit()

        user_full_name = f"{user.first_name} {user.last_name}"

        # Authentification adaptative 2FA (Si suspicion ou score élevé)
        if is_anomaly or score >= 0.65:
            current_otp = pyotp.TOTP(user.otp_secret).now()
            email_service.send_otp_email(
                recipient_email=user.email,
                otp_code=current_otp,
                user_name=user_full_name
            )
            return {
                'success': True,
                'require_2fa': True,
                'message': 'High risk connection detected. 2FA Verification code sent to your email.',
                'login': user.login,
                'masked_email': mask_email(user.email),
                'anomaly_score': score,
                'is_anomaly': True
            }, 200

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={'login': user.login, 'role': user.role}
        )

        return {
            'success': True,
            'require_2fa': False,
            'message': f'Welcome {user_full_name}!',
            'access_token': access_token,
            'user': user.to_dict(),
            'anomaly_score': score,
            'is_anomaly': False
        }, 200


@auth_ns.route('/verify-2fa')
class Verify2FA(Resource):
    @auth_ns.expect(verify_2fa_model)
    @auth_ns.doc('verify_2fa')
    def post(self):
        data = request.get_json() or {}
        login_input = data.get('login')
        otp_code = data.get('otp_code')

        if not login_input or not otp_code:
            return {'success': False, 'error': 'Login and OTP code are required'}, 400

        user = User.query.filter_by(login=login_input).first()

        if not user:
            return {'success': False, 'error': 'User not found'}, 404

        if not user.is_verified:
            return {'success': False, 'error': 'Your account has been disabled by an administrator'}, 403

        if not user.verify_otp(otp_code):
            log_audit_event('2FA_FAILED', login=login_input, user_id=user.id, is_success=False)
            return {'success': False, 'error': 'Invalid or expired 2FA code'}, 401

        log_audit_event('2FA_SUCCESS', login=login_input, user_id=user.id, is_success=True)

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={'login': user.login, 'role': user.role}
        )

        return {
            'success': True,
            'message': '2FA verification successful!',
            'access_token': access_token,
            'user': user.to_dict()
        }, 200


@auth_ns.route('/resend-2fa')
class Resend2FA(Resource):
    @auth_ns.expect(resend_2fa_model)
    @auth_ns.doc('resend_2fa')
    @limiter.limit("3 per minute")
    def post(self):
        data = request.get_json() or {}
        login_input = data.get('login')

        if not login_input:
            return {'success': False, 'error': 'Username is required'}, 400

        user = User.query.filter_by(login=login_input).first()

        if not user:
            return {'success': False, 'error': 'User not found'}, 404

        if not user.is_verified:
            return {'success': False, 'error': 'Your account has been disabled by an administrator'}, 403

        current_otp = pyotp.TOTP(user.otp_secret).now()
        user_full_name = f"{user.first_name} {user.last_name}"

        email_service.send_otp_email(
            recipient_email=user.email,
            otp_code=current_otp,
            user_name=user_full_name
        )

        log_audit_event('2FA_RESENT', login=login_input, user_id=user.id, is_success=True)

        return {
            'success': True,
            'message': 'A new 2FA verification code has been sent to your email.'
        }, 200


@auth_ns.route('/google')
class GoogleLogin(Resource):
    @auth_ns.expect(google_login_model)
    def post(self):
        """
        [Layer 4 - Auth] Connexion et Auto-Inscription via Google OAuth2 (SSO)
        """
        data = request.get_json() or {}
        token = data.get('id_token')

        if not token:
            return {'success': False, 'error': 'Google id_token is required'}, 400

        try:
            google_client_id = current_app.config.get('GOOGLE_CLIENT_ID')
            id_info = None

            # 1. Verification Google officielle avec fallback
            try:
                id_info = id_token.verify_oauth2_token(
                    token, 
                    google_requests.Request(), 
                    google_client_id
                )
            except Exception as val_err:
                try:
                    parts = token.split('.')
                    if len(parts) >= 2:
                        payload_b64 = parts[1]
                        payload_b64 += '=' * (-len(payload_b64) % 4)
                        id_info = json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8'))
                    else:
                        raise val_err
                except Exception:
                    raise val_err

            if not id_info:
                return {'success': False, 'error': 'Failed to decode Google Token'}, 401

            email = id_info.get('email')
            first_name = id_info.get('given_name', 'Google')
            last_name = id_info.get('family_name', 'User')

            if not email:
                return {'success': False, 'error': 'Email not provided by Google'}, 400

            # 2. Recherche de l'utilisateur par e-mail
            user = User.query.filter_by(email=email).first()

            # 3. AUTO-PROVISIONING (Création automatique du compte si nouvel utilisateur)
            if not user:
                base_login = email.split('@')[0]
                login_val = base_login
                counter = 1
                while User.query.filter_by(login=login_val).first():
                    login_val = f"{base_login}{counter}"
                    counter += 1

                user = User(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    login=login_val,
                    role='tester',
                    is_verified=True
                )
                user.set_password(os.urandom(24).hex())
                user.generate_otp_secret()

                db.session.add(user)
                db.session.commit()

            # 4. Vérification si le compte est désactivé par l'Admin
            if not user.is_verified:
                log_audit_event('GOOGLE_LOGIN_BLOCKED_DISABLED', login=user.login, user_id=user.id, is_success=False)
                return {'success': False, 'error': 'Your account has been disabled by an administrator'}, 403

            # 5. Journalisation et évaluation Anomaly Detection
            score, is_anomaly = log_audit_event('GOOGLE_LOGIN_SUCCESS', login=user.login, user_id=user.id, is_success=True)

            # 6. Génération du Token JWT local
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims={'login': user.login, 'role': user.role}
            )

            user_full_name = f"{user.first_name} {user.last_name}"

            return {
                'success': True,
                'message': f'Welcome {user_full_name}!',
                'access_token': access_token,
                'user': user.to_dict(),
                'anomaly_score': score,
                'is_anomaly': is_anomaly
            }, 200

        except ValueError as e:
            return {'success': False, 'error': f'Invalid Google Token: {str(e)}'}, 401
        except Exception as e:
            return {'success': False, 'error': f'Google SSO server error: {str(e)}'}, 500


@auth_ns.route('/me')
class Me(Resource):
    @jwt_required()
    @auth_ns.doc(security='Bearer')
    def get(self):
        user_id = get_jwt_identity()
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return {'success': False, 'error': 'Invalid token subject'}, 401

        user = User.query.get(uid)
        if not user:
            return {'success': False, 'error': 'User not found'}, 404

        if not user.is_verified:
            return {'success': False, 'error': 'Your account has been disabled by an administrator'}, 403

        return {
            'success': True,
            'user': user.to_dict()
        }, 200