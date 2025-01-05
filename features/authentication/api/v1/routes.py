from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from features.authentication.domain.services import AuthenticationService
from features.authentication.domain.models import User

auth_api = Blueprint('auth_api', __name__)

@auth_api.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['email', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    try:
        user, token = AuthenticationService.register_user(
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name'),
            last_name=data.get('last_name')
        )
        
        # TODO: Send activation email
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_api.route('/login', methods=['POST'])
def login():
    """User login."""
    data = request.get_json()
    
    # Validate required fields
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    
    user = AuthenticationService.verify_credentials(data['email'], data['password'])
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account not activated'}), 403
    
    # Create tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    })

@auth_api.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    
    return jsonify({'access_token': access_token})

@auth_api.route('/activate/<token>', methods=['POST'])
def activate(token):
    """Activate user account."""
    user = AuthenticationService.activate_account(token)
    if not user:
        return jsonify({'error': 'Invalid or expired activation token'}), 400
    
    return jsonify({
        'message': 'Account activated successfully',
        'user': user.to_dict()
    })

@auth_api.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset."""
    data = request.get_json()
    
    if not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
    
    token = AuthenticationService.create_password_reset_token(data['email'])
    if not token:
        return jsonify({'error': 'Email not found'}), 404
    
    # TODO: Send password reset email
    
    return jsonify({'message': 'Password reset instructions sent'})

@auth_api.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    """Reset password."""
    data = request.get_json()
    
    if not data.get('password'):
        return jsonify({'error': 'New password is required'}), 400
    
    user = AuthenticationService.reset_password(token, data['password'])
    if not user:
        return jsonify({'error': 'Invalid or expired reset token'}), 400
    
    return jsonify({
        'message': 'Password reset successful',
        'user': user.to_dict()
    })

@auth_api.route('/me', methods=['GET'])
@jwt_required()
def get_user():
    """Get current user info."""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()) 