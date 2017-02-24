# Flask-WTF v0.13 renamed Flask to FlaskForm
try:
    from flask_wtf import FlaskForm         # Try Flask-WTF v0.13+
except ImportError:
    from flask_wtf import Form as FlaskForm # Fallback to Flask-WTF v0.12 or older

from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import Required


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[Required()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

class PasswordForm(FlaskForm):
    old_password = PasswordField('Old Password', validators=[Required()])
    new_password1 = PasswordField('New Password', validators=[Required()])
    new_password2 = PasswordField('Retype New Password', validators=[Required()])
    submit = SubmitField('Submit')