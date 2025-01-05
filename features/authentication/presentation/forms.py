from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from features.authentication.domain.models import User

class LoginForm(FlaskForm):
    """Login form."""
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired()
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    """Registration form."""
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    first_name = StringField('First Name', validators=[
        Length(max=50)
    ])
    last_name = StringField('Last Name', validators=[
        Length(max=50)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')
    
    def validate_email(self, field):
        """Validate email is not already registered."""
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered')

class ForgotPasswordForm(FlaskForm):
    """Forgot password form."""
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    submit = SubmitField('Reset Password')

class ResetPasswordForm(FlaskForm):
    """Reset password form."""
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password') 