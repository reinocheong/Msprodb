from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import math

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'main.login' # Sets the login page endpoint
migrate = Migrate()

def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Load configuration
    app.config.from_object('config.Config')

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Import and register blueprints
    from . import routes
    app.register_blueprint(routes.main)

    # Define the user loader function
    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # Register custom template filter
    @app.template_filter('clean_nan')
    def clean_nan_filter(value, default=0):
        if value is None or (isinstance(value, (float, int)) and math.isnan(value)):
            return default
        return value

    return app