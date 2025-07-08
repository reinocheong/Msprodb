from flask import Flask
from .extensions import db, login_manager, migrate
from .routes import main as main_blueprint
from .models import User
import math

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Register blueprint
    app.register_blueprint(main_blueprint)

    # Define user loader
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
