from functools import wraps
from flask import session, redirect, url_for, request, jsonify
import jwt
from src.config.settings import JWT_SECRET

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            token = token.split(' ')[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user = data
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # First check session for web routes
        if 'signedin' in session:
            user = session['signedin']
            if user and 'roles' in user and 'admin' in user['roles']:
                return f(*args, **kwargs)
        
        # Then check Authorization header for API routes
        token = request.headers.get('Authorization')
        if token:
            try:
                token = token.split(' ')[1]  # Remove 'Bearer ' prefix
                data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
                if 'admin' in data.get('roles', []):
                    return f(*args, **kwargs)
            except:
                pass
        
        # If neither session nor token is valid, redirect to login
        return redirect(url_for('account.login'))
    return decorated

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'signedin' not in session:
            return redirect(url_for('account.login'))
        return f(*args, **kwargs)
    return decorated 