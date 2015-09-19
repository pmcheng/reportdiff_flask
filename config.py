import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    REPORT_DATABASE = os.path.join(basedir,'..','core','powerscribe','reportdiff_ps.db')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir,'..','core','powerscribe','users.db')
    
class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') 

config = {
    'development': DevelopmentConfig,
    'default': Config
}

