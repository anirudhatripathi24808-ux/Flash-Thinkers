import os
from pathlib import Path
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.database import init_db, db_session
from backend.sockets import socketio
from backend.routes.auth_routes import auth_bp
from backend.routes.teacher_routes import teacher_bp
from backend.routes.student_routes import student_bp
from backend.routes.analytics_routes import analytics_bp

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

def create_app(test_config=None):
    app = Flask(__name__, static_folder=str(FRONTEND_DIR / "assets"), static_url_path="/assets")
    app.config.from_object(Config)
    
    if test_config:
        app.config.update(test_config)
        
    # Enable CORS for cross-origin frontend (e.g. GitHub Pages) and local development
    CORS(app, supports_credentials=True, origins="*", resources={r"/api/*": {"origins": "*"}})
    
    # Initialize SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(analytics_bp)
    
    # Ensure database tables and initial subjects exist
    with app.app_context():
        init_db()
        
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()
        
    # Health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "FLASHNOVA Futuristic EdTech Platform",
            "version": "2.0.0"
        })
        
    # Serve Frontend Pages for unified local / container run
    @app.route("/")
    def serve_index():
        return send_from_directory(str(FRONTEND_DIR), "index.html")
        
    @app.route("/student")
    @app.route("/student.html")
    def serve_student():
        return send_from_directory(str(FRONTEND_DIR), "student.html")
        
    @app.route("/teacher")
    @app.route("/teacher.html")
    def serve_teacher():
        return send_from_directory(str(FRONTEND_DIR), "teacher.html")
        
    @app.route("/<path:path>")
    def serve_static_page(path):
        if (FRONTEND_DIR / path).exists():
            return send_from_directory(str(FRONTEND_DIR), path)
        return send_from_directory(str(FRONTEND_DIR), "index.html")
        
    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    print(f"Starting FLASHNOVA on http://localhost:{port}")
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
