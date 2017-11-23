from flask import Flask, flash, redirect, render_template, request, session, abort, jsonify, url_for
from flask_pymongo import PyMongo

from bokeh.plotting import output_file, show, figure
from bokeh.palettes import Spectral11
from bokeh.embed import components 

from datetime import datetime
from pymongo import MongoClient

import bcrypt
import json
import pandas
import re
import requests
#import simplejson as json
import sys


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


# helper functions for register password check
def has_nums(s):
	return bool(re.search(r'[0-9]', s))

def has_special(s):
	return bool(re.search(r'\W+$', s))

def has_capital(s):
	return bool(re.search(r'[A-Z]', s))

def has_lower(s):
	return bool(re.search(r'[a-z]', s))

@app.route("/register", methods=["POST"])
def register():
	users = mongo.db.users
	existing_user = users.find_one({'name' : request.form['username']})
	# check if the password has at least 3 of [A-Z], [a-z], [0-9], special chars
	print(has_nums(request.form['password']))
	if (has_nums(request.form['password']) + 
	   has_special(request.form['password']) +
	   has_capital(request.form['password']) +
	   has_lower(request.form['password'])) < 3:
	   return render_template("create_account.html", password_error=True)

	if existing_user is None:
		if request.form['password'] == request.form['confirmPassword']:
			hashpass = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
			users.insert({'name' : request.form['username'], 'password' : hashpass, 'stocks': []})
			session['user'] = request.form['username']
			return redirect(url_for("home"))
		else:
			return render_template("create_account.html", confirm_error=True, username_error=False)

	return render_template("create_account.html", confirm_error=False, username_error=True)



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



# helper functions for getting stock data based on ticker
def stock_info(ticker):
	
	# https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=GOOG&interval=1min&apikey=8HEWLV32V6QMXG1L
	av_intraday_url = "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=" + ticker + "&interval=1min&apikey=8HEWLV32V6QMXG1L"
	print("1: ")
	result = requests.get(av_intraday_url)
	print(result.status_code)
	result = result.json()
	last_refreshed = result["Meta Data"]["3. Last Refreshed"]
	close_price = float(result["Time Series (1min)"][last_refreshed]["4. close"])

	av_daily_url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=" + ticker + "&apikey=8HEWLV32V6QMXG1L"
	print("2: ")
	result = requests.get(av_daily_url)
	print(result.status_code)
	result = result.json()
	daily_time_series = result["Time Series (Daily)"]
	ordered_daily_time_series = sorted(daily_time_series.items(), key = lambda x:datetime.strptime(x[0], '%Y-%m-%d'), reverse=True)
	previous_day = ordered_daily_time_series[1]
	previous_close_price = float(previous_day[1][ "4. close"])

	most_recent_day = ordered_daily_time_series[0]
	open_price = float(most_recent_day[1]["1. open"])
	low_price = float(most_recent_day[1]["3. low"])
	high_price = float(most_recent_day[1]["2. high"])
	volume = float(most_recent_day[1]["5. volume"])

	av_daily_url_full = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=" + ticker + "&outputsize=full&apikey=8HEWLV32V6QMXG1L"
	print("3: ")
	result = requests.get(av_daily_url_full)
	print(result.status_code)
	result = result.json()
	daily_time_series_full = result["Time Series (Daily)"]
	#list of tuples in this format: ('2017-11-22', {'5. volume': '2764505', '2. high': '181.7300', '3. low': '180.8000', '4. close': '181.0267', '1. open': '181.3000'})
	ordered_daily_time_series_full = sorted(daily_time_series_full.items(), key = lambda x:datetime.strptime(x[0], '%Y-%m-%d'), reverse=True)
	return close_price, previous_close_price, open_price, low_price, high_price, volume, ordered_daily_time_series_full



@app.route("/profile", methods=["GET"])
def profile():
	try:
		users = mongo.db.users
		login_user = users.find_one({'name' : session['user']})
		stocks = login_user['stocks']

		total_cost = 0
		total_market_value = 0
		total_gain = 0
		total_gain_percentage = 0

		for stock in stocks:
			ticker = stock['ticker']
			print(ticker)
			stock['price'], previous_close_price, *rest = stock_info(ticker)
			print(stock['price'])
			print(previous_close_price)
			
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

	except:
		return "ERROR: AlphaVantage server is overloaded"




'''
- change button if already got stock in portfolio
'''
@app.route("/search", methods=["POST"])
def search():
	try:
		#convert ticker to all-caps
		ticker = request.form['search'].upper()

		#verify that stock ticker exists
		yahoo_url = "http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en".format(ticker)
		result = requests.get(yahoo_url).json()

		name_found = False
		for x in result['ResultSet']['Result']:
			if x['symbol'] == ticker:
				name = x['name'] #get stock name from ticker
				name_found = True
		if name_found == False:
			return "ERROR: invalid ticker"

		close_price, previous_close_price, open_price, low_price, high_price, volume, ordered_daily_time_series_full = stock_info(ticker)

		price_change = close_price - previous_close_price
		price_change_percentage = (close_price - previous_close_price) / close_price * 100
		if price_change > 0:
			price_change_str = '+$' + '{0:.2f}'.format(price_change) + ' (+' + '{0:.2f}'.format(price_change_percentage) + '%)'
		else:
			price_change_str = '-$' + '{0:.2f}'.format(-price_change) + ' (-' + '{0:.2f}'.format(-price_change_percentage) + '%)'
		
		volume_str = "{:.2f}".format(volume / 10**6) + "M"

		#get current share holdings of stock
		users = mongo.db.users
		stocks = users.find_one({'name' : session["user"]})["stocks"]
		current_holdings = 0
		for stock in stocks:
			if stock["ticker"] == ticker:
				current_holdings = stock["shares"]

		#create stock's closing price chart
		x_date = []
		y_close = []

		#ordered_daily_time_series_full is a list of tuples in this format: ('2017-11-22', {'5. volume': '2764505', '2. high': '181.7300', '3. low': '180.8000', '4. close': '181.0267', '1. open': '181.3000'})
		for day in ordered_daily_time_series_full:
			x_date.append(pandas.to_datetime(day[0]))
			y_close.append(float(day[1]['4. close']))

		p = figure(title='Historical Stock Prices for %s' % ticker, x_axis_label='Date', x_axis_type='datetime')
		p.line(x = x_date, y = y_close, line_width = 2)

		script, div = components(p)
	   
		return render_template("search.html", ticker = ticker, close_price = close_price, previous_close_price = previous_close_price, price_change_str = price_change_str, open_price = open_price, low_price = low_price, high_price = high_price, volume = volume_str, name = name, script = script, div = div, current_holdings = current_holdings)
		
	except:
		return "ERROR: AlphaVantage server is overloaded"



@app.route("/add_stock", methods=["POST"])
def add_stock():

	users = mongo.db.users
	ticker = request.form['ticker']
	close_price = float(request.form['close_price'])

	#check for empty user input
	if len(request.form['shares']) == 0:
		shares = 0
	else:
		shares = int(request.form['shares'])

	stocks = users.find_one({'name' : session["user"]})["stocks"]
	existing_stock = None
	for stock in stocks:
		if stock["ticker"] == ticker:
			existing_stock = stock

	if existing_stock is None:
		users.update_one(
			{ 'name' : session["user"] },
			{'$push': {
				'stocks': {
					'name': request.form['name'],
					'ticker': ticker,
					'price': 0.0, #placeholder
					'change': 0.0, #placeholder
					'change_percentage': 0.0, #placeholder
					'shares': int(shares),
					'cost': close_price * int(shares),
					'market_value': 0.0, #placeholder
					'gain': 0.0, #placeholder
					'gain_percentage': 0.0, #placeholder
					}
				}
			}
		)

	else:
		new_shares = existing_stock["shares"] + shares
		if new_shares == 0:
			users.update(
				{ 'name': session["user"], 'stocks.ticker': ticker },
				{ '$pull': { 
					'stocks': {'ticker': ticker }
					}
				}
			)

		else:
			new_cost = close_price * shares + existing_stock["cost"]
			users.update(
				{ 'name': session["user"], 'stocks.ticker': ticker },
				{ '$set': {
					'stocks.$.shares': new_shares,
					'stocks.$.cost': new_cost,
					}
				}
			)

	return redirect(url_for("profile"))


if __name__ == "__main__":
	app.secret_key = 'mysecret'
	app.run(host="0.0.0.0", port=8000)
