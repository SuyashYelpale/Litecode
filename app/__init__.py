from flask import Flask, session
from datetime import datetime
from app.routes import main
from app.auth import auth_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = "super_secret_key"

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth_bp)

    # Context processors
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    @app.context_processor
    def inject_user():
        return {'user': session.get('user')}

    return app