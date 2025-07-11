from flask import Flask, session, current_app
from datetime import datetime
from app.routes import main
from .routes import main
from app.auth import auth_bp
import os

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

    # Debug route - only in development
    if os.environ.get('FLASK_ENV') == 'development':
        @app.route('/routes')
        def list_routes():
            import urllib.parse
            output = []
            for rule in current_app.url_map.iter_rules():
                if not rule.endpoint.startswith('static'):
                    methods = ','.join(rule.methods)
                    line = urllib.parse.unquote(f"{rule.endpoint:50s} {methods:20s} {rule}")
                    output.append(line)
            return '<br>'.join(sorted(output))

    return app