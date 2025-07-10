from flask import Flask
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.doctor_routes import doctor_bp
from routes.student_routes import student_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecretkey123"

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doctor_bp, url_prefix="/doctor")
    app.register_blueprint(student_bp, url_prefix="/student")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)


