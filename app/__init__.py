from flask import Flask, session, current_app
from datetime import datetime
import os


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'super_secret_key_dev')

    # Import blueprints inside create_app to avoid circular imports
    with app.app_context():
        from app.routes import main as main_blueprint
        from app.auth import auth_bp as auth_blueprint
        
        # Register blueprints with unique names
        app.register_blueprint(main_blueprint)
        app.register_blueprint(auth_blueprint)

    # Context processors
    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    @app.context_processor
    def inject_user():
        return {'user': session.get('user')}

    # Debug routes
    if os.getenv('FLASK_ENV') == 'development' or app.debug:
        @app.route('/debug/routes')
        def list_routes():
            import urllib.parse
            output = []
            for rule in current_app.url_map.iter_rules():
                if not rule.endpoint.startswith('static'):
                    methods = ','.join(rule.methods)
                    line = urllib.parse.unquote(f"{rule.endpoint:50s} {methods:20s} {rule}")
                    output.append(line)
            return '<br>'.join(sorted(output))

        @app.route('/debug/session')
        def show_session():
            return dict(session)

    return app