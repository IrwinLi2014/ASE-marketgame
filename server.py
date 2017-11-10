from flask import Flask, flash, redirect, render_template, request, session, abort, jsonify, url_for
from flask_pymongo import PyMongo

from bokeh.plotting import output_file, show, figure
from bokeh.palettes import Spectral11
from bokeh.embed import components 

import bcrypt
import datetime
import pandas
import pandas_datareader.data as web
import requests
import simplejson as json
import sys
from pymongo import MongoClient


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
            return render_template("create_account.html", password_error=True, username_error=False)

    return render_template("create_account.html", password_error=False, username_error=True)



@app.route("/login", methods=["POST"])
def login():
    users = mongo.db.users
    login_user = users.find_one({'name' : request.form['username']})

    if login_user:
        if bcrypt.hashpw(request.form['password'].encode('utf-8'), login_user['password']) == login_user['password']:
            session['user'] = request.form['username']
            return redirect(url_for('home'))

    return render_template("index.html", error=True)



@app.route("/logout", methods=["POST"])
def logout():
    del session['user']
    return redirect(url_for("index"))
       


@app.route("/profile", methods=["GET"])
def profile():
    users = mongo.db.users
    login_user = users.find_one({'name' : session['user']})
    stocks = login_user['stocks']

    total_cost = 0
    total_market_value = 0
    total_gain = 0
    total_gain_percentage = 0

    for stock in stocks:
        ticker = stock['ticker']
        data = web.DataReader(ticker, 'google', datetime.datetime.now(), datetime.datetime.now())
        stock['price'] = data['Close'].iloc[-1]
        previous_close_price = data['Close'].iloc[-2]
        stock['change'] = stock['price'] - previous_close_price
        stock['change_percentage'] = stock['change'] / stock['price'] * 100
        stock['market_value'] = stock['price'] * stock['shares']
        stock['gain'] = stock['market_value'] - stock['cost']
        if stock['shares'] == 0:
            stock['gain_percentage'] = 0
        else:
            stock['gain_percentage'] = stock['gain'] / stock['cost'] * 100

        total_cost += stock['cost']
        total_market_value += stock['market_value'] 
        total_gain = total_market_value - total_cost
        total_gain_percentage = total_gain / total_cost * 100

    return render_template("profile.html", stocks=stocks, total_cost = total_cost, total_market_value = total_market_value, total_gain = total_gain, total_gain_percentage = total_gain_percentage)



'''
- change button if already got stock in portfolio
'''
@app.route("/search", methods=["POST"])
def search():

    #convert ticker to all-caps
    ticker = request.form['search'].upper()

    #verify that stock ticker exists
    url = "http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en".format(ticker)
    result = requests.get(url).json()

    name_found = False
    for x in result['ResultSet']['Result']:
        if x['symbol'] == ticker:
            name = x['name'] #get stock name from ticker
            name_found = True
    if name_found == False:
        return "ERROR: invalid ticker"

    #get stock data from ticker input
    data = web.DataReader(ticker, 'google', datetime.datetime.now(), datetime.datetime.now())
    close_price = data['Close'].iloc[-1]
    previous_close_price = data['Close'].iloc[-2]
    price_change = close_price - previous_close_price
    price_change_percentage = (close_price - previous_close_price) / close_price * 100
    if price_change > 0:
        price_change_str = '+$' + '{0:.2f}'.format(price_change) + ' (+' + '{0:.2f}'.format(price_change_percentage) + '%)'
    else:
        price_change_str = '-$' + '{0:.2f}'.format(-price_change) + ' (-' + '{0:.2f}'.format(-price_change_percentage) + '%)'

    open_price = data['Open'].iloc[-1]
    low_price = data['Low'].iloc[-1]
    high_price = data['High'].iloc[-1]
    volume = data['Volume'].iloc[-1]

    #create stock's closing price chart
    api_url = 'https://www.quandl.com/api/v1/datasets/WIKI/%s.json?api_key=gVz7XbzeecyxHdkCn8yB' % ticker
    session = requests.Session()
    session.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
    raw_data = session.get(api_url)
    a = raw_data.json()

    df = pandas.DataFrame(a['data'], columns=a['column_names'])

    df['Date'] = pandas.to_datetime(df['Date'])

    p = figure(title='Historical Stock Prices for %s' % ticker, x_axis_label='date', x_axis_type='datetime')
    p.line(x=df['Date'].values, y=df['Close'].values,line_width=2)

    script, div = components(p)
   
    return render_template("search.html", ticker = ticker, close_price = close_price, previous_close_price = previous_close_price, price_change_str = price_change_str, open_price = open_price, low_price = low_price, high_price = high_price, volume = volume, name = name, script = script, div = div)



@app.route("/add_stock", methods=["POST"])
def add_stock():

    users = mongo.db.users
    data = web.DataReader(request.form['ticker'], 'google', datetime.datetime.now(), datetime.datetime.now())
    #check for empty user input

    if len(request.form['shares']) == 0:
        shares = 0
    else:
        shares = int(request.form['shares'])

    existing_stock = users.find_one({'stocks.ticker' : request.form['ticker']})
    if existing_stock is None:
        users.update_one(
            { 'name' : session["user"] },
            {'$push': {
                'stocks': {
                    'name': request.form['name'],
                    'ticker': request.form['ticker'],
                    'price': 0.0, #placeholder
                    'change': 0.0, #placeholder
                    'change_percentage': 0.0, #placeholder
                    'shares': int(shares),
                    'cost': data['Close'].iloc[-1] * int(shares),
                    'market_value': 0.0, #placeholder
                    'gain': 0.0, #placeholder
                    'gain_percentage': 0.0, #placeholder
                    }
                }
            }
        )

    else:
        cur_stock = existing_stock['stocks']
        print(cur_stock)
        existing_shares = cur_stock[0]['shares']

        users.update(
            { 'name': session["user"], 'stocks.ticker': request.form['ticker'] },
            { '$set': {
                'stocks.$.shares': existing_shares + shares,
                'stocks.$.cost': data['Close'].iloc[-1] * shares,
                }
            }
        )

        cur_stock = existing_stock['stocks']
        print(cur_stock)
        


    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.secret_key = 'mysecret'
    app.run(host="0.0.0.0", port=8000)
