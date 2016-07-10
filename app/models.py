# from datetime import datetime
# from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from . import db, login_manager
        
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64),
                         nullable=False, unique=True, index=True)
    role = db.Column(db.Integer)
    password = db.Column(db.String(128))
    firstname = db.Column(db.String(64))
    lastname = db.Column(db.String(64))
    nickname = db.Column(db.String(64))
    ps_id = db.Column(db.Integer)
    grad_date = db.Column(db.String(64))

    # For greater security we should be generating and storing a password hash
    
    #@property
    #def password(self):
    #    raise AttributeError('password is not a readable attribute')

    #@password.setter
    #def password(self, password):
    #    self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        #return check_password_hash(self.password_hash, password)    
        return (self.password==password)

class Login(db.Model):
    __tablename__ = 'logins'
    id = db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    timestamp=db.Column(db.String(64))    

class ReportView(db.Model):
    __tablename__ = 'report_views'
    id = db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False)
    accession=db.Column(db.String(64))
    timestamp=db.Column(db.String(64))    

class Report(db.Model):
    __bind_key__ = 'reports'
    __tablename__ = 'study'
    site = db.Column(db.String(128))
    accession = db.Column(db.String(64), primary_key=True)
    timestamp = db.Column(db.String(64))
    proceduredescription = db.Column(db.String(128))
    procedurecode = db.Column(db.String(64))
    modality = db.Column(db.String(64))
    resident = db.Column(db.String(128))
    residentID = db.Column(db.String(64))
    attending = db.Column(db.String(128))
    attendingID = db.Column(db.String(64))
    prelim = db.Column(db.String(65536))
    prelim_timestamp = db.Column(db.String(64))
    final = db.Column(db.String(65536))
    final_timestamp = db.Column(db.String(64))
    diff_score = db.Column(db.Integer)
    diff_score_percent = db.Column(db.Float)
    
    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
