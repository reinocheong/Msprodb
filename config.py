import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'local_dev.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Add this line to enable pre-ping, which checks database connections before use
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    DEBUG = False