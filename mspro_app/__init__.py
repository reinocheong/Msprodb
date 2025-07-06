import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    # --- Configuration ---
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///msprodata.db'

    # --- Initialize Extensions ---
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from . import routes
        app.register_blueprint(routes.main)

        from .models import User
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(user_id)
            
        login_manager.login_view = 'main.login'

    return app
