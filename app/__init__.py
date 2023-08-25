from flask import Flask
from flask_session import Session
from flask_cors import CORS
from .views import auth_blueprint, spotify_blueprint

app = Flask(__name__)
app.config.from_object('config.Config')
app.register_blueprint(auth_blueprint)
app.register_blueprint(spotify_blueprint)
Session(app)
CORS(app,
     origins=["*"],
     supports_credentials=True)
