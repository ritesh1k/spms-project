from flask import Flask
from config.config import Config


def create_app():
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY

    from app.routes import bp
    app.register_blueprint(bp)

    return app
