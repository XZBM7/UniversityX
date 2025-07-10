from flask import Flask
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.doctor_routes import doctor_bp
from routes.student_routes import student_bp
import os
from pymongo import MongoClient

def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecretkey123"

    # Connect to MongoDB from environment variable
    mongo_uri = os.environ.get("MONGO_URI")
    client = MongoClient(mongo_uri)
    db = client.get_default_database()  # Automatically gets DB from URI

    # Store db in app context if needed later
    app.config["MONGO_DB"] = db

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doctor_bp, url_prefix="/doctor")
    app.register_blueprint(student_bp, url_prefix="/student")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
