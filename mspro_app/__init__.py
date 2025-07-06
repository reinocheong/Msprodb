from flask import Flask
import os

def create_app():
    # The static_folder needs to be relative to the instance path, 
    # or an absolute path. Let's define it relative to the app's root.
    app = Flask(__name__, instance_relative_config=True)
    
    # Correct path for static files when app is in a sub-directory
    app.static_folder = os.path.join(os.path.dirname(app.root_path), 'static')
    app.template_folder = os.path.join(os.path.dirname(app.root_path), 'mspro_app', 'templates')


    # Configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///local_dev.db').replace("postgres://", "postgresql://", 1),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # Initialize extensions
    from .extensions import db, login_manager, migrate
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Register Blueprints
    from . import routes
    app.register_blueprint(routes.main)

    # User loader
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    login_manager.login_view = 'main.login'

    return app