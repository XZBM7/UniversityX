from flask import Flask, g
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.doctor_routes import doctor_bp
from routes.student_routes import student_bp
from pymongo import MongoClient

def create_app():
    app = Flask(__name__)
    app.secret_key = "supersecretkey123"

    # ضع رابط الاتصال مباشرة هنا
    MONGO_URI = "mongodb+srv://katafafa9:MyPass1234@universityx.6slxjqo.mongodb.net/university_system?retryWrites=true&w=majority&appName=UniversityX"

    client = MongoClient(MONGO_URI)
    db = client.get_default_database()  # تأخذ قاعدة البيانات من الرابط

    app.config["MONGO_DB"] = db

    @app.before_request
    def before_request():
        g.db = app.config["MONGO_DB"]

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doctor_bp, url_prefix="/doctor")
    app.register_blueprint(student_bp, url_prefix="/student")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
