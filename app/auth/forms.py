from flask_wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import Required


class LoginForm(Form):
    username = StringField('Username', validators=[Required()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

class PasswordForm(Form):
    old_password = PasswordField('Old Password', validators=[Required()])
    new_password1 = PasswordField('New Password', validators=[Required()])
    new_password2 = PasswordField('Retype New Password', validators=[Required()])
    submit = SubmitField('Submit')
    