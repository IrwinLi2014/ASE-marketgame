from flask import Flask, flash, redirect, render_template, request, session, abort, jsonify, url_for
from flask_pymongo import PyMongo
from flask_pymongo import MongoClient

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
import updater


app = Flask(__name__)

app.config['MONGO_DBNAME'] = 'winydb'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/winydb'

mongo = PyMongo(app)

global_id = 0

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

		r = requests.get("https://finance.yahoo.com/gainers?offset=0&count=25")
		tickers = re.findall("<a href=\"/quote/(.+?)\?", r.text)
		
		stocks = [] #list of stock dictionaries
		count = 0
		for ticker in tickers:
			if count >= 5:
				break
			try:
				#get name
				yahoo_url = "http://d.yimg.com/autoc.finance.yahoo.com/autoc?query={}&region=1&lang=en".format(ticker)
				result = requests.get(yahoo_url).json()
				name_found = False
				for x in result['ResultSet']['Result']:
					if x['symbol'] == ticker:
						name = x['name'] #get stock name from ticker
						name_found = True
				if name_found == False:
					return "ERROR: invalid ticker"

				#get other information
				close_price, previous_close_price, open_price, low_price, high_price, volume = updater.stock_info(ticker)
				
				#create dictionary
				stock = {
					"name": name,
					"ticker": ticker, 
					"price": close_price,
					"change": close_price - previous_close_price,
					"change_percentage": (close_price - previous_close_price) / previous_close_price * 100,
				}
				if stock["change_percentage"] >= 15:
					continue
				stocks.append(stock)
				count += 1

			except:
				continue

		fp_url = "https://newsapi.org/v2/top-headlines?sources=financial-post&apiKey=e439238bd7bc4cde8d2937a0178554b0"
		result = requests.get(fp_url).json()

		#print(result);
		news_links = []
		img_links = []

		links=[]
		for x in result['articles']:
			links.append((x['url'], x['urlToImage'], x['title']))
			#print(x['title']);
			#news_links.append(x['url'])
			#img_links.append(x['urlToImage'])

		#print(links)
		links=links[0:4]
		#news_links = news_links[0:4]
		#img_links = img_links[0:4]
		return render_template("home.html", user=session["user"], stocks=stocks, links=links)
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
			users.insert({'name' : request.form['username'], 'password' : hashpass, 'stocks': [], 'admin': False, 'group': ''})
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


@app.route("/profile", methods=["GET"])
def profile():
	users = mongo.db.users
	login_user = users.find_one({'name' : session['user']})

	# if user is an admin, then load the admin page
	if login_user["admin"]:
		return render_template("admin.html")

	stocks = login_user['stocks']

	total_cost = 0
	total_market_value = 0
	total_gain = 0
	total_gain_percentage = 0

	for stock in stocks:
		ticker = stock['ticker']
		# stock['price'], previous_close_price, *rest = stock_info(ticker)
		stock['price'], previous_close_price, *rest = updater.stock_info(ticker)
		users.update_one(
			{'name': session["user"], 'stocks.ticker': stock["ticker"]},
			{'$set': {'stocks.$.price': stock['price']}}
		)
		
		stock['change'] = stock['price'] - previous_close_price
		stock['change_percentage'] = stock['change'] / stock['price'] * 100
		stock['market_value'] = stock['price'] * stock['shares']
		stock['gain'] = stock['market_value'] - stock['cost']
		stock['gain_percentage'] = stock['gain'] / stock['cost'] * 100

		total_cost += stock['cost']
		total_market_value += stock['market_value'] 
		total_gain = total_market_value - total_cost
		total_gain_percentage = total_gain / total_cost * 100

	return render_template("profile.html", stocks=stocks, total_cost=total_cost, total_market_value=total_market_value, total_gain=total_gain, total_gain_percentage=total_gain_percentage)



@app.route("/search", methods=["POST"])
def search():
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

	# close_price, previous_close_price, open_price, low_price, high_price, volume, ordered_daily_time_series_full = stock_info(ticker)
	close_price, previous_close_price, open_price, low_price, high_price, volume = updater.stock_info(ticker)
	ordered_daily_time_series_full = updater.ordered_daily_time_series_full(ticker)

	price_change = close_price - previous_close_price
	price_change_percentage = (close_price - previous_close_price) / close_price * 100
	if price_change > 0:
		price_change_str = '+$' + '{0:.2f}'.format(price_change) + ' (+' + '{0:.2f}'.format(price_change_percentage) + '%)'
	elif price_change < 0:
		price_change_str = '-$' + '{0:.2f}'.format(-price_change) + ' (-' + '{0:.2f}'.format(-price_change_percentage) + '%)'
	else: #price_change == 0
		price_change_str = '$' + '{0:.2f}'.format(price_change) + ' (' + '{0:.2f}'.format(price_change_percentage) + '%)'
	
	# volume_str = "{:.2f}".format(volume / 10**6) + "M"
	volume_str = volume

	#get current share holdings of stock
	users = mongo.db.users
	login_user = users.find_one({'name' : session["user"]})
	stocks = login_user["stocks"]

	###########################
	# TODO: RESET GROUP NAMES #
	###########################
	in_game = login_user["group"] != ""
	groups = mongo.db.groups
	group = groups.find_one({"name": login_user["group"]})
	current_holdings = 0
	max_shares = 0
	money = 0
	if in_game:
		max_shares = group["money"] // close_price
		money = group["money"]
	for stock in stocks:
		if stock["ticker"] == ticker:
			current_holdings = stock["shares"]

	#create stock's closing price chart
	x_date = []
	y_close = []

	#ordered_daily_time_series_full is a list of tuples in this format: ('2017-11-22', {'5. volume': '2764505', '2. high': '181.7300', '3. low': '180.8000', '4. close': '181.0267', '1. open': '181.3000'})
	for day in ordered_daily_time_series_full:
		x_date.append(pandas.to_datetime(day[0]))
		# y_close.append(float(day[1]['4. close']))
		y_close.append(day[4])

	p = figure(title='Historical Stock Prices for %s' % ticker, x_axis_label='Date', x_axis_type='datetime')
	p.line(x=x_date, y=y_close, line_width=2)

	script, div = components(p)

	return render_template("search.html",
                           ticker=ticker,
                           close_price=close_price,
                           previous_close_price=previous_close_price,
                           price_change_str=price_change_str,
                           open_price=open_price,
                           low_price=low_price,
                           high_price=high_price,
                           volume=volume_str,
                           name=name,
                           script=script,
                           div=div,
                           current_holdings=current_holdings,
                           max_shares=max_shares,
                           money=money,
                           in_game=in_game)
		


@app.route("/add_stock", methods=["POST"])
def add_stock():
	print(request.form)

	if request.form["games"] == "true":
		users = mongo.db.users
		name = users.find_one({'name' : session["user"]})["group"]
		users = mongo.db.groups
		current = users.find_one({'name' : name})
		stocks = current["stocks"]
	else:
		users = mongo.db.users
		current = users.find_one({'name' : session["user"]})
		stocks = current["stocks"]
		name = session["user"]

	print(name)
	ticker = request.form['ticker']
	close_price = float(request.form['close_price'])

	# add stock to database
	updater.add_stock(ticker, close_price)

	# #check for empty user input
	# if len(request.form['shares']) == 0:
	# 	shares = 0
	# else:
	# 	shares = int(request.form['shares'])

	#check for empty user input
	shares = 0
	if len(request.form['shares']) == 0 or request.form['shares'] == "0":
		return redirect(url_for("profile"))
	else:
		shares = int(request.form['shares'])

	existing_stock = None
	for stock in stocks:
		if stock["ticker"] == ticker:
			existing_stock = stock

	if existing_stock is None:
		users.update_one(
			{'name' : name},
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
				{'name': name, 'stocks.ticker': ticker},
				{'$pull': {
					'stocks': {'ticker': ticker}
					}
				}
			)
		else:
			new_cost = close_price * shares + existing_stock["cost"]
			users.update(
				{'name': name, 'stocks.ticker': ticker},
				{'$set': {
					'stocks.$.shares': new_shares,
					'stocks.$.cost': new_cost,
					}
				}
			)

	if request.form["games"] == "true":
		users.update_one(
			{'name': name},
			{'$set': {'money': current["money"] - close_price * int(shares)}}
		)
		return redirect(url_for("games"))
	return redirect(url_for("profile"))




@app.route("/games")
def games():


    users = mongo.db.users
    login_user = users.find_one({'name' : session['user']})
    games = mongo.db.games
    cursor = games.find({})
    groups = mongo.db.groups

    results = [res for res in cursor]
    cur_date = datetime.now()
    invited_groups = []
    for res in results:

        game_start = datetime.strptime(res.get("start_date"), '%Y-%m-%d')
        game_end = datetime.strptime(res.get("end_date"), '%Y-%m-%d')
        reg_start = datetime.strptime(res.get("reg_start_date"), '%Y-%m-%d')
        reg_end = datetime.strptime(res.get("reg_end_date"), '%Y-%m-%d')

        id = res["id"]
        global global_id

        if cur_date > game_start and cur_date < game_end:
            global_id = id
            game_groups = res["groups"]
            for group in game_groups:
                users_list = groups.find_one({'name': group})
                if login_user['name'] in users_list['users']:
                    stocks = users_list['stocks']

                    total_cost = 0
                    total_market_value = 0
                    total_gain = 0
                    total_gain_percentage = 0

                    for stock in stocks:
                        ticker = stock['ticker']
                        # stock['price'], previous_close_price, *rest = stock_info(ticker)
                        stock['price'], previous_close_price, *rest = updater.stock_info(ticker)
                        groups.update_one(
                            {'name': users_list["name"], 'stocks.ticker': stock["ticker"]},
                            {'$set': {'stocks.$.price': stock['price']}}
                        )

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

                    return render_template("game.html",
                                           stocks=users_list["stocks"],
                                           total_cost=total_cost,
                                           total_market_value=total_market_value,
                                           total_gain=total_gain,
                                           total_gain_percentage=total_gain_percentage,
                                           group=users_list["name"],
                                           money=users_list["money"])

        if cur_date >= reg_start and cur_date <= reg_end:
            global_id = id
            # you want to start rendering the template
            # you want to retrieve the list of groups the user was invited to
            
            group_list = res["groups"]

            # check if the login user is already in the database for the groups for the game
            for group_name in group_list:
                cur_group = groups.find_one({'name' : group_name})
                if login_user['name'] in cur_group['users']:
                    return render_template("not_game.html")
            for group_name in group_list:
                cur_group = groups.find_one({'name' : group_name})
                if cur_group is not None:
                    invitees = cur_group['invitees']
                    if login_user['name'] in invitees:
                        invited_groups.append(group_name)

            # retrieve a list of all users to invite
            all_users = []
            for res in users.find({}):
                if res['name'] == login_user['name']:
                    continue
                elif res['group'] == "":
                    all_users.append(res['name'])
            return render_template("register.html", id=id, invited_groups=invited_groups, all_users=all_users)
    return "ERROR: Currently not a registration or a game period"


def id_of_game(game):
    id = 0
    cursor = game.find({})

    results = [res for res in cursor]
    for res in results:
        id += 1
    return id

def check_date_overlap(date1, date2, date3, date4):
    return max(date1, date3) < min(date2, date4)


@app.route("/add_game", methods=["POST"])
def add_game():
    users = mongo.db.users
    login_user = users.find_one({'name' : session['user']})
    games = mongo.db.games
    new_id = id_of_game(games) + 1

    if request.form['regdate1'] > request.form['regdate2']:
        return render_template("admin.html", registration_error=True)
    if request.form['date1'] > request.form['date2']:
        return render_template("admin.html", game_error=True)
    if request.form['regdate2'] > request.form['date1']:
        return render_template("admin.html", reg_game_error=True)
    if datetime.strptime(request.form['regdate2'], '%Y-%m-%d') < datetime.now():
        return render_template("admin.html", cur_reg_error=True)
    if datetime.strptime(request.form['date1'], '%Y-%m-%d') < datetime.now():
        return render_template("admin.html", cur_game_error=True)

    cursor = games.find({})
    results = [res for res in cursor]
    for res in results:
        overlap_1 = check_date_overlap(request.form['date1'], request.form['date2'], res['start_date'], res['end_date'])
        overlap_2 = check_date_overlap(request.form['regdate1'], request.form['regdate2'], res['reg_start_date'], res['reg_end_date'])
        if overlap_1 == True:
            return render_template("admin.html", game_overlap=True)
        if overlap_2 == True:
            return render_template("admin.html", registration_overlap=True)

    games.insert({'id' : new_id,
                  'groups' : [],
                  'start_date': request.form['date1'],
                  'end_date': request.form['date2'],
                  'reg_start_date': request.form['regdate1'],
                  'reg_end_date': request.form['regdate2'],
                  'admin': login_user['name']})
    return render_template("game_creation.html", error = True)

@app.route("/add_admin", methods=["POST"])
def add_admin():
    users = mongo.db.users
    added_admin = users.find_one({'name' : request.form['admin_user']})
    if added_admin is None:
        return "ERROR: User does not exist"
    users.update(
        {'name': request.form['admin_user']},
        {'$set': {'admin': True}}
    )
    return render_template("admin.html", error=True)


@app.route("/join_group", methods=["POST", "GET"])
def join_group():
    users = mongo.db.users
    login_user = users.find_one({'name' : session['user']})
    groups = mongo.db.groups
    group_name = request.form.get('option')
    groups.update(
                { 'name': group_name},
                { '$push': {
                    'users': login_user['name']
                }
                }
            )
    group = groups.find_one({"name": group_name})

    games = mongo.db.games
    cur_game = games.find_one({'id' : global_id})
    if cur_game is None:
        return render_template('not_game.html', error=True)

    if datetime.strptime(cur_game['start_date'], '%Y-%m-%d') <= datetime.now() and datetime.strptime(cur_game['end_date'], '%Y-%m-%d') >= datetime.now():
        users.update_one(
            {"name": login_user["name"]},
            {"$set": {"group": group_name}}
        )
        # return render_template("game.html", error=True)
        total_cost = 0.0
        for stock in group["stocks"]:
        	total_cost += stock["cost"]

        return render_template("game.html",
                               stocks=group["stocks"],
                               total_cost=total_cost,
                               total_market_value=0.0,
                               total_gain=0.0,
                               total_gain_percentage=0.0,
                               group=group_name,
                               money=100000)
    return render_template('not_game.html', error=True)
   
@app.route("/create_group", methods=["POST", "GET"])
def create_group():
    users = mongo.db.users
    groups = mongo.db.groups
    games = mongo.db.games
    login_user = users.find_one({'name' : session['user']})
    group_name = request.form['group_name']
    invitees_string = request.form['txtName']
    invitees_list = [x.strip() for x in invitees_string[:-1].split(',')]
    users_list = [login_user['name']]
    owner = login_user['name']

    cursor = groups.find({})
    results = [res for res in cursor]
    for res in results:
        if group_name == res['name']:
            return render_template('register.html', group_name_exists=True)



    # Add a group with the group name and the invitees list: group name, invitees, users
    groups.insert({'name' : group_name, 'owner' : owner, 'invitees': invitees_list, 'users': users_list, 'stocks': [], 'money': 100000})

    # add the group name to the game
    games.update({'id' : global_id}, {'$push': {'groups': group_name}})

    # Check if the game is currently ongoing or not and determine which template to render
    cur_game = games.find_one({'id' : global_id})
    if cur_game is None:
        return render_template('not_game.html', error=True)

    if datetime.strptime(cur_game['start_date'], '%Y-%m-%d') <= datetime.now() and datetime.strptime(cur_game['end_date'], '%Y-%m-%d') >= datetime.now():
        users.update_one(
            {"name": login_user["name"]},
            {"$set": {"group": group_name}}
        )
        # return render_template("game.html", error=True)
        return render_template("game.html", stocks=[], total_cost = 0.0, total_market_value = 0.0, total_gain = 0.0, total_gain_percentage = 0.0, group=group_name, money=100000)
    return render_template('not_game.html', error=True)


@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    groups = mongo.db.groups
    stocks = mongo.db.stocks
    unranked = []
    for group in groups.find({}):
    	value = group["money"]
    	for stock in group["stocks"]:
    		price = stocks.find_one({"ticker": stock["ticker"]})["price"]
    		groups.update_one(
				{'name': group["name"], 'stocks.ticker': stock["ticker"]},
				{'$set': {'stocks.$.price': price}}
			)
    		value += price * stock["shares"]
    	unranked.append((group["name"], value))
    ranked = sorted(unranked, key=lambda k: k[1], reverse=True)
    return render_template("leaderboard.html", teams=ranked)

if __name__ == "__main__":
	app.secret_key = 'mysecret'
	app.run(host="0.0.0.0", port=8000)
