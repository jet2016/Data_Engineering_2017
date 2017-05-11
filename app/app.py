from flask import Flask
from flask import render_template
from os import path

'''
REMEMBER TO EXPORT FLASK_APP=app.py
Then do "flask run"
'''


d = path.dirname(__file__)
app = Flask(__name__)

@app.route("/")
@app.route("/index.html")
def index():
	return render_template('index.html')
