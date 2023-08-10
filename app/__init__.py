from flask import Flask

app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY'

from app import routes