"""
Application Factory Flask.

Ce module contient la fonction create_app() qui crée et configure
l'application Flask avec toutes ses extensions.
"""
from flask import Flask
from flask_cors import CORS
from flask_restx import Api, Resource, Namespace

from app.config import config
from app.extensions import db, migrate, jwt, limiter


def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialiser les extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    
    # Importer les modèles pour qu'ils soient connus de SQLAlchemy
    from app.models import User, AuditLog
    
    # CRÉATION AUTOMATIQUE DES TABLES MANQUANTES DANS DEV.DB
    with app.app_context():
        db.create_all()
    
    # Configuration CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:4200"]
        }
    })
    
    # Swagger API Configuration
    authorizations = {
        'Bearer': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': "JWT : tape 'Bearer <access_token>'"
        }
    }
    
    api = Api(
        app,
        version='1.0',
        title='KPIT Auth Platform API',
        description='AI-Enhanced Authentication Platform - REST API Documentation',
        doc='/docs',
        prefix='/api',
        authorizations=authorizations,
        security='Bearer'
    )
    
    # ============================================
    # REGISTER NAMESPACES (ROUTES)
    # ============================================
    
    # 1. Health check namespace
    ns_health = Namespace('health', description='Health check endpoints')
    api.add_namespace(ns_health)
    
    @ns_health.route('')
    class HealthCheck(Resource):
        def get(self):
            return {
                'status': 'healthy',
                'message': 'KPIT Auth Platform API is running',
                'version': '1.0.0'
            }
    
    # 2. Authentication Namespace (/api/auth)
    from app.routes.auth import auth_ns
    api.add_namespace(auth_ns)
    
    # 3. User Management Namespace (/api/users)  <-- AJOUTÉ ICI
    from app.routes.users import users_ns
    api.add_namespace(users_ns)
    
    # 4. Test Manager Namespace (/api/tests)
    from app.routes.test_manager import test_ns
    api.add_namespace(test_ns)
    
    return app