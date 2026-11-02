"""
Modèle User - Représente un utilisateur dans la base de données.

Layer 1 : BCrypt Password Hashing & RBAC
Layer 3 : TOTP / 2FA Secret Key pour Authentification Adaptative
"""
from datetime import datetime
import bcrypt
import pyotp

from app.extensions import db


class User(db.Model):
    """
    Modèle User - Un utilisateur de l'application.
    """

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)

    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    login = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Hash BCrypt
    password = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), default='viewer', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # --- LAYER 3 : 2FA / TOTP SECRET ---
    otp_secret = db.Column(db.String(32), nullable=True) # Clé secrète 2FA (32 car. Base32)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # ============================================
    # ALIAS DE COMPATIBILITÉ POUR IS_VERIFIED
    # ============================================
    @property
    def is_verified(self) -> bool:
        """Alias pour is_active (assure la compatibilité totale frontend/API)"""
        return self.is_active

    @is_verified.setter
    def is_verified(self, value: bool) -> None:
        self.is_active = value

    def __repr__(self):
        return f'<User {self.login} ({self.email})>'

    # ============================================
    # LAYER 1 — BCRYPT METHODS
    # ============================================

    def set_password(self, plain_password: str) -> None:
        if not plain_password:
            raise ValueError('Password cannot be empty')

        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
        self.password = hashed.decode('utf-8')

    def check_password(self, plain_password: str) -> bool:
        if not plain_password or not self.password:
            return False

        stored = self.password

        if self._is_bcrypt_hash(stored):
            try:
                return bcrypt.checkpw(
                    plain_password.encode('utf-8'),
                    stored.encode('utf-8')
                )
            except (ValueError, TypeError):
                return False

        if stored == plain_password:
            self.set_password(plain_password)
            try:
                db.session.add(self)
                db.session.commit()
            except Exception:
                db.session.rollback()
            return True

        return False

    @staticmethod
    def _is_bcrypt_hash(value: str) -> bool:
        if not value or not isinstance(value, str):
            return False
        return value.startswith(('$2a$', '$2b$', '$2y$')) and len(value) >= 50

    # ============================================
    # LAYER 3 — 2FA / TOTP METHODS
    # ============================================

    def generate_otp_secret(self) -> str:
        """Génère une nouvelle clé secrète aléatoire TOTP (32 caractères)."""
        self.otp_secret = pyotp.random_base32()
        return self.otp_secret

    def get_totp(self) -> pyotp.TOTP:
     """Retourne l'objet TOTP configuré avec la clé secrète de l'utilisateur."""
     if not self.otp_secret:
        self.generate_otp_secret()  # <-- Corrigé avec self
     return pyotp.TOTP(self.otp_secret)

    def verify_otp(self, code: str) -> bool:
        """
        Vérifie le code OTP à 6 chiffres saisi par l'utilisateur.
        valid_window=1 permet d'accepter le code avec une tolérance de 30 secondes.
        """
        if not code or not self.otp_secret:
            return False
        totp = self.get_totp()
        return totp.verify(code, valid_window=1)

    # ============================================
    # SERIALISATION
    # ============================================

    def to_dict(self, include_password=False):
        data = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'login': self.login,
            'role': self.role,
            'is_active': self.is_active,
            'is_verified': self.is_active, # Pour synchronisation Frontend
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_password:
            data['password'] = self.password

        return data

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'