from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS

from webapp.views.session import session
from webapp.views.rs import rs

app = Flask(__name__)
CORS(app)

app.register_blueprint(session)
app.register_blueprint(rs)

if __name__ == '__main__':
  app.run(debug=True)