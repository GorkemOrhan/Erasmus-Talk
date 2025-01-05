from datetime import datetime, timedelta
import secrets
from typing import Optional, Tuple
from app.factory import db
from features.authentication.domain.models import User, ActivationToken, PasswordResetToken

class AuthenticationService:
    @staticmethod
    def register_user(email: str, password: str, first_name: str = None, last_name: str = None) -> Tuple[User, str]:
        """Register a new user and create activation token."""
        user = User(email=email, password=password, first_name=first_name, last_name=last_name)
        db.session.add(user)
        
        # Create activation token
        token = secrets.token_urlsafe(32)
        activation = ActivationToken(
            user=user,
            token=token,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        db.session.add(activation)
        db.session.commit()
        
        return user, token
    
    @staticmethod
    def verify_credentials(email: str, password: str) -> Optional[User]:
        """Verify user credentials."""
        user = User.query.filter_by(email=email).first()
        if user and user.verify_password(password):
            return user
        return None
    
    @staticmethod
    def activate_account(token: str) -> Optional[User]:
        """Activate user account using token."""
        activation = ActivationToken.query.filter_by(
            token=token,
            used=False
        ).first()
        
        if not activation or activation.expires_at < datetime.utcnow():
            return None
        
        user = activation.user
        user.is_active = True
        activation.used = True
        db.session.commit()
        
        return user
    
    @staticmethod
    def create_password_reset_token(email: str) -> Optional[str]:
        """Create password reset token for user."""
        user = User.query.filter_by(email=email).first()
        if not user:
            return None
        
        token = secrets.token_urlsafe(32)
        reset_token = PasswordResetToken(
            user=user,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(reset_token)
        db.session.commit()
        
        return token
    
    @staticmethod
    def reset_password(token: str, new_password: str) -> Optional[User]:
        """Reset user password using token."""
        reset = PasswordResetToken.query.filter_by(
            token=token,
            used=False
        ).first()
        
        if not reset or reset.expires_at < datetime.utcnow():
            return None
        
        user = reset.user
        user.password = new_password
        reset.used = True
        db.session.commit()
        
        return user 