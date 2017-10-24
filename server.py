
from flask import Flask, flash, redirect, render_template, request, session, abort, jsonify
from flask_pymongo import PyMongo
app = Flask(__name__)


app.config['MONGO_DBNAME'] = 'winydb'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/winydb'

mongo = PyMongo(app)

@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/create_account", methods=["GET"])
def create_account():
    return render_template("create_account.html")

@app.route("/home", methods=["GET"])
def home():
    return render_template("home.html")

@app.route("/login", methods=["POST"])
def login():
    # TODO: Everything

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
