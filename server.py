
from flask import Flask, flash, redirect, render_template, request, session, abort, jsonify, url_for
from flask_pymongo import PyMongo
import bcrypt

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
    if "user" in session:
        return render_template("home.html")
    return redirect(url_for("index"))

@app.route("/register", methods=["POST"])
def register():
    users = mongo.db.users
    existing_user = users.find_one({'name' : request.form['username']})
    if existing_user is None:
        if request.form['password'] == request.form['confirmPassword']:
            hashpass = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
            users.insert({'name' : request.form['username'], 'password' : hashpass, 'stocks': []})
            session['user'] = request.form['username']
            return redirect(url_for("home"))
        else:
            return "ERROR: Passwords do not match"
    
    return "ERROR: Username already exists"

@app.route("/login", methods=["POST"])
def login():
    users = mongo.db.users
    login_user = users.find_one({'name' : request.form['username']})
    print(login_user)

    if login_user:
        if bcrypt.hashpw(request.form['password'].encode('utf-8'), login_user['password']) == login_user['password']:
            session['user'] = request.form['username']
            print("made it???")
            return redirect(url_for('home'))

    return "ERROR: Invalid username or password"



'''
Yiming TO-DO:
- error message for wrong stock ticker 
- change button if already got stock in portfolio
- make pretty
'''
@app.route("/search", methods=["POST"])
def search():
    return render_template("search.html", ticker=request.form['search'])


@app.route("/add_stock", methods=["POST"])
def add_stock():

    users = mongo.db.users
    print(session)

    users.update_one(
        { 'name' : session["user"] },
        {'$push': {
            'stocks': {
                'ticker': request.form['ticker'],
                'date': request.form['date'],
                'shares': request.form['shares'],
                'price': request.form['price'],
                'commission': request.form['commission']
                }
            }
        }
    )


    return redirect(url_for("home"))


if __name__ == "__main__":
    app.secret_key = 'mysecret'
    app.run(host="0.0.0.0", port=8000)
