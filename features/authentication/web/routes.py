from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from features.authentication.domain.services import AuthenticationService
from features.authentication.presentation.forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm

auth_web = Blueprint('auth_web', __name__)

@auth_web.route('/')
def index():
    """Home page."""
    return render_template('index.html')

@auth_web.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('auth_web.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = AuthenticationService.verify_credentials(form.email.data, form.password.data)
        if user:
            if not user.is_active:
                flash('Please activate your account first. Check your email for the activation link.', 'warning')
                return redirect(url_for('auth_web.login'))
            
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('auth_web.index'))
        
        flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html', form=form)

@auth_web.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('auth_web.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user, token = AuthenticationService.register_user(
            email=form.email.data,
            password=form.password.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data
        )
        
        # Send activation email
        activation_url = url_for('auth_web.activate', token=token, _external=True)
        # TODO: Send email with activation_url
        
        flash('Registration successful! Please check your email to activate your account.', 'success')
        return redirect(url_for('auth_web.login'))
    
    return render_template('auth/register.html', form=form)

@auth_web.route('/activate/<token>')
def activate(token):
    """Activate user account."""
    user = AuthenticationService.activate_account(token)
    if user:
        flash('Your account has been activated! You can now login.', 'success')
    else:
        flash('Invalid or expired activation link.', 'danger')
    
    return redirect(url_for('auth_web.login'))

@auth_web.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('auth_web.index'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        token = AuthenticationService.create_password_reset_token(form.email.data)
        if token:
            reset_url = url_for('auth_web.reset_password', token=token, _external=True)
            # TODO: Send email with reset_url
            
            flash('Password reset instructions have been sent to your email.', 'info')
            return redirect(url_for('auth_web.login'))
        
        flash('Email address not found.', 'danger')
    
    return render_template('auth/forgot_password.html', form=form)

@auth_web.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Reset password."""
    if current_user.is_authenticated:
        return redirect(url_for('auth_web.index'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = AuthenticationService.reset_password(token, form.password.data)
        if user:
            flash('Your password has been reset! You can now login.', 'success')
            return redirect(url_for('auth_web.login'))
        
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('auth_web.forgot_password'))
    
    return render_template('auth/reset_password.html', form=form)

@auth_web.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth_web.index'))

@auth_web.route('/profile')
@login_required
def profile():
    """User profile."""
    return render_template('auth/profile.html') 