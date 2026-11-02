from flask import request
from flask_restx import Namespace, Resource, fields
from app.extensions import db
from app.models.user import User
from app.services.audit_service import log_audit_event
from flask_jwt_extended import jwt_required, get_jwt_identity

users_ns = Namespace('users', description='User Management Operations')

user_role_model = users_ns.model('UserRoleUpdate', {
    'role': fields.String(required=True, description='New role: admin, tester, auditor, viewer')
})

user_create_model = users_ns.model('UserCreateByAdmin', {
    'first_name': fields.String(required=True),
    'last_name': fields.String(required=True),
    'email': fields.String(required=True),
    'login': fields.String(required=True),
    'password': fields.String(required=True),
    'role': fields.String(required=True, description='admin, tester, auditor, viewer')
})

@users_ns.route('')
class UserList(Resource):
    @jwt_required()
    @users_ns.doc('list_users')
    def get(self):
        """Récupère la liste complète des utilisateurs"""
        users = User.query.order_by(User.id.desc()).all()
        return {
            'success': True,
            'count': len(users),
            'users': [u.to_dict() for u in users]
        }, 200

    @jwt_required()
    @users_ns.expect(user_create_model)
    @users_ns.doc('create_user_by_admin')
    def post(self):
        """Créer un utilisateur manuellement par un Admin"""
        current_user_id = get_jwt_identity()
        admin_user = User.query.get(current_user_id)

        if not admin_user or admin_user.role != 'admin':
            return {'success': False, 'error': 'Unauthorized: Admin privileges required'}, 403

        data = request.get_json() or {}
        required = ['first_name', 'last_name', 'email', 'login', 'password', 'role']
        for field in required:
            if not data.get(field):
                return {'success': False, 'error': f'Missing field: {field}'}, 400

        if User.query.filter_by(email=data['email']).first():
            return {'success': False, 'error': 'Email already exists'}, 409

        if User.query.filter_by(login=data['login']).first():
            return {'success': False, 'error': 'Username already taken'}, 409

        new_user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            login=data['login'],
            role=data.get('role', 'tester')
        )
        new_user.set_password(data['password'])
        new_user.generate_otp_secret()

        try:
            db.session.add(new_user)
            db.session.commit()
            log_audit_event(
                'ADMIN_USER_CREATED',
                login=new_user.login,
                user_id=new_user.id,
                details=f"User {new_user.login} created with role {new_user.role} by Admin {admin_user.login}",
                is_success=True
            )
            return {
                'success': True,
                'message': 'User created successfully',
                'user': new_user.to_dict()
            }, 201
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'Database error: {str(e)}'}, 500


@users_ns.route('/<int:user_id>')
class UserDetail(Resource):
    @jwt_required()
    @users_ns.doc('delete_user')
    def delete(self, user_id):
        """Supprimer un utilisateur de la plateforme"""
        current_user_id = get_jwt_identity()
        admin_user = User.query.get(current_user_id)

        if not admin_user or admin_user.role != 'admin':
            return {'success': False, 'error': 'Unauthorized: Admin privileges required'}, 403

        # Sécurité : un Admin ne peut pas se supprimer lui-même
        if int(current_user_id) == int(user_id):
            return {'success': False, 'error': 'You cannot delete your own admin account'}, 400

        target_user = User.query.get(user_id)
        if not target_user:
            return {'success': False, 'error': 'User not found'}, 404

        target_login = target_user.login

        try:
            db.session.delete(target_user)
            db.session.commit()
            log_audit_event(
                'ADMIN_USER_DELETED',
                login=target_login,
                user_id=user_id,
                details=f"User {target_login} deleted by Admin {admin_user.login}",
                is_success=True
            )
            return {
                'success': True,
                'message': f'User {target_login} deleted successfully'
            }, 200
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'Database error: {str(e)}'}, 500


@users_ns.route('/<int:user_id>/role')
class UserRoleUpdate(Resource):
    @jwt_required()
    @users_ns.expect(user_role_model)
    @users_ns.doc('update_user_role')
    def patch(self, user_id):
        """Mise à jour du rôle d'un utilisateur"""
        current_user_id = get_jwt_identity()
        admin_user = User.query.get(current_user_id)

        if not admin_user or admin_user.role != 'admin':
            return {'success': False, 'error': 'Unauthorized: Admin privileges required'}, 403

        target_user = User.query.get(user_id)
        if not target_user:
            return {'success': False, 'error': 'User not found'}, 404

        data = request.get_json() or {}
        new_role = data.get('role')
        allowed_roles = ['admin', 'tester', 'auditor', 'viewer']

        if new_role not in allowed_roles:
            return {'success': False, 'error': f'Invalid role. Allowed roles: {allowed_roles}'}, 400

        old_role = target_user.role
        target_user.role = new_role

        try:
            db.session.commit()
            log_audit_event(
                'USER_ROLE_UPDATED',
                login=target_user.login,
                user_id=target_user.id,
                details=f"Role changed from {old_role} to {new_role} by Admin {admin_user.login}",
                is_success=True
            )
            return {
                'success': True,
                'message': f'Role updated to {new_role} successfully',
                'user': target_user.to_dict()
            }, 200
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'Database error: {str(e)}'}, 500

@users_ns.route('/<int:user_id>/status')
class UserStatusToggle(Resource):
    @jwt_required()
    @users_ns.doc('toggle_user_status')
    def patch(self, user_id):
        """Activer ou désactiver un compte utilisateur"""
        current_user_id = get_jwt_identity()
        admin_user = User.query.get(current_user_id)

        if not admin_user or admin_user.role != 'admin':
            return {'success': False, 'error': 'Unauthorized: Admin privileges required'}, 403

        if int(current_user_id) == int(user_id):
            return {'success': False, 'error': 'You cannot disable your own admin account'}, 400

        target_user = User.query.get(user_id)
        if not target_user:
            return {'success': False, 'error': 'User not found'}, 404

        # Inverse le statut actuel
        target_user.is_verified = not target_user.is_verified

        try:
            db.session.commit()
            status_str = "ENABLED" if target_user.is_verified else "DISABLED"
            log_audit_event(
                'USER_STATUS_CHANGED',
                login=target_user.login,
                user_id=target_user.id,
                details=f"Account status set to {status_str} by Admin {admin_user.login}",
                is_success=True
            )
            return {
                'success': True,
                'message': f'User account is now {status_str}',
                'is_verified': target_user.is_verified
            }, 200
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': f'Database error: {str(e)}'}, 500        