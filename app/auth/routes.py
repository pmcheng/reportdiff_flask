from flask import render_template, current_app, request, redirect, url_for, flash
from flask.ext.login import login_user, logout_user, login_required, current_user
from ..models import User, Login
from .. import db
from . import auth
from .forms import LoginForm, PasswordForm
import datetime
from sqlalchemy import func

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if not current_app.config['DEBUG'] and not current_app.config['TESTING'] \
            and not request.is_secure:
        return redirect(url_for('.login', _external=True, _scheme='https'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(func.lower(User.username)==func.lower(form.username.data)).first()
        #user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.verify_password(form.password.data):
            flash('Invalid username or password.')
            return redirect(url_for('.login'))
        login_user(user, form.remember_me.data)
        
        login = Login(user_id=user.id,timestamp=datetime.datetime.now())
        db.session.add(login)
        
        #current_user.numlogins+=1
        #current_user.lastlogin=datetime.datetime.now()
        #db.session.add(current_user._get_current_object())
        db.session.commit()
        
        return redirect(request.args.get('next') or url_for('reports.index'))
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('reports.index'))

@auth.route('/password', methods=['GET', 'POST'])
@login_required    
def password():
    form = PasswordForm()
    if form.validate_on_submit():
        if not current_user.verify_password(form.old_password.data):
            flash('Old password is incorrect.')
        elif (form.new_password1.data!=form.new_password2.data):
            flash('New passwords do not match.')
        else:
            current_user.password = form.new_password1.data
            db.session.add(current_user._get_current_object())
            db.session.commit()
            flash('Your password has been changed.')
            return redirect(url_for('reports.index'))
    return render_template('auth/password.html', form=form)