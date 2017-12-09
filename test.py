import pytest
from server import *
import pandas
import unittest
from unittest.mock import patch
import flask_pymongo
import updater
import datetime
import sched
import time

TEST_DB = 'new_test.db'


class MarketGameTests(unittest.TestCase):
	def setUp(self):
		app.secret_key = 'super secret key'
		app.config['TESTING'] = True
		app.config['MONGODB_DATABASE'] = 'new_test'
		self.app = app.test_client()

	def tearDown(self):
		with app.app_context():
			mongo.db.users.delete_many({})
			mongo.db.groups.delete_many({})
			mongo.db.games.delete_many({})



###############
#### tests ####
###############

	def test_index(self):
		response = self.app.get("/index")
		self.assertEqual(response.status_code, 200)

	def test_create_account(self):
		response = self.app.get("/create_account")
		self.assertEqual(response.status_code, 200)

	def test_home_redirect(self):
		response = self.app.get("/home")
		self.assertEqual(response.status_code, 302)

	def register(self, username, password, confirmPassword):
		return self.app.post(
			'/register',
			data=dict(username=username, password=password, confirmPassword=confirmPassword),
			follow_redirects=True
		)

	def test_register(self):
		response = self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.assertEqual(response.status_code, 200)



	def test_register_password_fail(self):
		response = self.register('abc@gmail.com', 'Hello123', 'nopenope')
		self.assertEqual("<strong>ERROR:</strong> Passwords do not match" in response.data.decode("utf-8"), True)
		self.assertEqual(response.status_code, 200)

		response = self.register('abc@gmail.com', 'nopenope', 'nopenope')
		self.assertTrue("Password must have at least 3 of" in response.data.decode("utf-8"))
		self.assertEqual(response.status_code, 200)

	def test_register_username_fail(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		response = self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.assertEqual("<strong>ERROR:</strong> Username already exists" in response.data.decode("utf-8"), True)
		self.assertEqual(response.status_code, 200)



	def login(self, username, password):
		return self.app.post('/login', data=dict(username=username, password=password))

	def test_login(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		response = self.login('abc@gmail.com', 'Hello123')
		self.assertEqual(response.status_code, 302)

	def test_login_fail(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		response = self.login('abc@gmail.com', 'nopenope')
		self.assertEqual("<strong>ERROR:</strong> Invalid username or password" in response.data.decode("utf-8"), True)
		self.assertEqual(response.status_code, 200)


	def add_stock(self, name, ticker, shares, close_price, games):
		return self.app.post('/add_stock', data=dict(name=name, ticker=ticker, shares=shares, close_price=close_price, games=games))

	def test_add_stock(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login("abc@gmail.com", "Hello123")
		response_1 = self.add_stock('Google', 'GOOG', "5", "5", "false")
		response_2 = self.add_stock('Google', 'GOOG', "5", "5", "false")
		response_3 = self.add_stock('Google', 'GOOG', "0", "5", "false") #test empty user input for shares
		self.assertEqual(response_1.status_code, 302)
		self.assertEqual(response_2.status_code, 302)
		self.assertEqual(response_3.status_code, 302)
		with app.app_context():
			user = mongo.db.users.find_one({'name' : "abc@gmail.com"})
		stocks = user["stocks"]

		found = False
		for stock in stocks:
			if stock['ticker'] == 'GOOG':
				found = True
				print("found")
				self.assertEqual(stock['shares'], 10)

		assert found
		# if not found:
		# 	assert False

		response_4 = self.add_stock('Apple', 'AAPL', "", "5", "false")
		self.assertEqual(response_4.status_code, 302)
		for stock in stocks:
			self.assertTrue(stock['ticker'] != 'AAPL')

		response_5 = self.add_stock('Facebook', 'FB', "5", "5", "false")
		response_6 = self.add_stock('Facebook', 'FB', "-5", "5", "false")
		self.assertEqual(response_5.status_code, 302)
		self.assertEqual(response_6.status_code, 302)
		for stock in stocks:
			self.assertTrue(stock['ticker'] != 'FB')
			# if stock['ticker'] == 'FB':
			# 	assert False
			
	def test_add_stock_game(self):
		today = datetime.date.today()
		tomorrow = today + datetime.timedelta(days=1)
		reg_start_date = today - datetime.timedelta(days=2)
		reg_end_date = today - datetime.timedelta(days=1)

		# format dates to string
		today = datetime.datetime.strftime(today, '%Y-%m-%d')
		tomorrow = datetime.datetime.strftime(tomorrow, '%Y-%m-%d')
		reg_start_date = datetime.datetime.strftime(reg_start_date, '%Y-%m-%d')
		reg_end_date = datetime.datetime.strftime(reg_end_date, '%Y-%m-%d')

		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login("abc@gmail.com", "Hello123")

		with app.app_context():
			mongo.db.groups.insert_one({
				'name': 'group_one',
				'stocks': [],
				'total_cost': 1000,
				'money': 100000,
				'users': []
			})
			mongo.db.games.insert_one({
				'id': 0,
				'reg_start_date': reg_start_date,
				'reg_end_date': reg_end_date,
				'start_date': today,
				'end_date': tomorrow
			})

		self.join_group('group_one')

		response_1 = self.add_stock('Google', 'GOOG', "5", "5", "true")
		response_2 = self.add_stock('Google', 'GOOG', "5", "5", "true") 
		response_3 = self.add_stock('Google', 'GOOG', "0", "5", "true") #test empty user input for shares
		self.assertEqual(response_1.status_code, 302)
		self.assertEqual(response_2.status_code, 302)
		self.assertEqual(response_3.status_code, 302)
		with app.app_context():
			group = mongo.db.groups.find_one({'name' : "group_one"})
		stocks = group["stocks"]

		found = False
		for stock in stocks:
			if stock['ticker'] == 'GOOG':
				found = True
				print(stock)
				self.assertEqual(stock['shares'], 10)

		assert found

		response_4 = self.add_stock('Apple', 'AAPL', "", "5", "true")
		self.assertEqual(response_4.status_code, 302)
		for stock in stocks:
			self.assertTrue(stock['ticker'] != 'AAPL')

		response_5 = self.add_stock('Facebook', 'FB', "5", "5", "true")
		response_6 = self.add_stock('Facebook', 'FB', "-5", "5", "true")
		self.assertEqual(response_5.status_code, 302)
		self.assertEqual(response_6.status_code, 302)
		for stock in stocks:
			self.assertTrue(stock['ticker'] != 'FB')

	def test_profile(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login("abc@gmail.com", "Hello123")
		response_1 = self.add_stock('Google', 'GOOG', "5", "5", "false")
		self.assertEqual(response_1.status_code, 302)

		response_2 = self.app.get("/profile")
		self.assertEqual(response_2.status_code, 200)
		self.assertEqual("<td>GOOG</td>" in response_2.data.decode("utf-8"), True)

	def test_profile_admin(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.add_admin("abc@gmail.com")
		self.login('abc@gmail.com', 'Hello123')
		response = self.app.get("/profile")
		self.assertEqual(response.status_code, 200)
		self.assertTrue("<h4>Create a new game</h4>" in response.data.decode('utf-8'))

	def add_admin(self, admin_user):
		return self.app.post('/add_admin', data=dict(admin_user=admin_user))

	def test_add_admin(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.register('def@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')
		response = self.add_admin('def@gmail.com')
		with app.app_context():
			user = mongo.db.users.find_one({'name' : 'def@gmail.com'})
		admin_status = user['admin']
		self.assertEqual(admin_status, True)
		self.assertEqual(response.status_code, 200)

		# does not exist
		response = self.add_admin('aaa@gmail.com')
		self.assertEqual(response.status_code, 200)
		self.assertTrue("ERROR: User does not exist" in response.data.decode('utf-8'))

	# add game tests: check all overlap/errors, then check correctness
	def add_game(self, regdate1, regdate2, date1, date2):
		return self.app.post('/add_game', data = dict(regdate1=regdate1, regdate2=regdate2, date1=date1, date2=date2))

	def test_add_game_date_error(self):
		day0 = datetime.date.today()
		day1 = day0 + datetime.timedelta(days=1)
		day2 = day0 + datetime.timedelta(days=2)
		day3 = day0 + datetime.timedelta(days=3)

		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')

		# registration error
		self.add_game(day1, day0, day2, day3)
		with app.app_context():
			game_id_1 = mongo.db.games.find_one({'id' : 1})
		self.assertEqual(game_id_1, None)

		# game error
		self.add_game(day0, day1, day3, day2)
		with app.app_context():
			game_id_2 = mongo.db.games.find_one({'id' : 1})
		self.assertEqual(game_id_2, None)

		# reg_game_error
		self.add_game(day0, day2, day1, day3)
		with app.app_context():
			game_id_3 = mongo.db.games.find_one({'id' : 1})
		self.assertEqual(game_id_3, None)

		# cur_reg_error
		self.add_game(day0 + datetime.timedelta(days=-2), day0 + datetime.timedelta(days=-1), day1, day2)
		with app.app_context():
			game_id_4 = mongo.db.games.find_one({'id' : 1})
		self.assertEqual(game_id_4, None)

		# cur_game_error
		self.add_game('2017-12-01', '2017-12-07', '2017-12-07', '2017-12-22')
		with app.app_context():
			game_id_5 = mongo.db.games.find_one({'id' : 1})
		self.assertEqual(game_id_5, None)

	def test_add_game_overlap_error(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')
		self.add_game('2018-02-02', '2018-02-05', '2018-03-01', '2018-03-22')

		# registration overlap error
		self.add_game('2018-02-04', '2018-02-07', '2018-04-01', '2018-04-22')
		with app.app_context():
			game_id_1 = mongo.db.games.find_one({'id' : 2})
		self.assertEqual(game_id_1, None)

		# game overlap error
		self.add_game('2018-01-02', '2018-01-07', '2018-03-01', '2018-03-22')
		with app.app_context():
			game_id_2 = mongo.db.games.find_one({'id' : 2})
		self.assertEqual(game_id_2, None)

	def test_add_game(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')
		self.add_game('2018-02-02', '2018-02-05', '2018-03-01', '2018-03-22')
		with app.app_context():
			game_id = mongo.db.games.find_one({'id' : 1})
		self.assertEqual(game_id['id'], 1)


	def join_group(self, group_name):
		return self.app.post('/join_group', data=dict(option=group_name))

	def test_join_group(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')

		# test game does not exist
		response = self.join_group('group_one')
		self.assertTrue("This is not a current game period." in response.data.decode("utf-8"))

		with app.app_context():
			mongo.db.groups.insert_one({'name': 'group_one', 'stocks': [], 'total_cost': 1000})
			mongo.db.games.insert_one({'id': 0, 'reg_start_date': '2017-11-01', 'reg_end_date': '2017-11-30', 'start_date': '2017-12-07', 'end_date': '2018-05-02'})

		response = self.join_group('group_one')

		with app.app_context():
			group_user = mongo.db.groups.find_one({'name': 'group_one'})
			user_group = mongo.db.users.find_one({'name': 'abc@gmail.com'})

		self.assertEqual(group_user['users'], ['abc@gmail.com'])
		self.assertEqual(user_group['group'], 'group_one')
		self.assertEqual(response.status_code, 200)

	def create_group(self, group_name, txtName):
		return self.app.post('/create_group', data=dict(group_name = group_name, txtName = txtName))

	def test_create_group(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')

		with app.app_context():
			mongo.db.games.insert_one({'id': 1, 'reg_start_date': '2017-11-01', 'reg_end_date': '2017-11-30', 'start_date': '2017-12-07', 'end_date': '2018-05-02'})

		response = self.create_group('group_one', 'def@gmail.com,ghi@gmail.com,')

		with app.app_context():
			group = mongo.db.groups.find_one({'name' : 'group_one'})
			game = mongo.db.games.find_one({'id' : 1})

		self.assertEqual(group['owner'], 'abc@gmail.com')
		self.assertEqual(group['users'], ['abc@gmail.com'])
		self.assertEqual(group['invitees'], ['def@gmail.com', 'ghi@gmail.com'])
		

		self.assertEqual(response.status_code, 200)
		self.assertTrue("<h1>This is not a current game period. Please click the button below to register for the next game!</h1>" in response.data.decode("utf-8"))

	def test_create_group_ongoing(self):
		today = datetime.date.today()
		tomorrow = today + datetime.timedelta(days=1)

		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')

		with app.app_context():
			mongo.db.games.insert_one({
				'id': 0,
				'reg_start_date': datetime.datetime.strftime(today, '%Y-%m-%d'),
				'reg_end_date': datetime.datetime.strftime(tomorrow, '%Y-%m-%d'),
				'start_date': datetime.datetime.strftime(today, '%Y-%m-%d'),
				'end_date': datetime.datetime.strftime(tomorrow, '%Y-%m-%d')
			})

		response = self.create_group('group_one', 'def@gmail.com,ghi@gmail.com,')

		with app.app_context():
			group = mongo.db.groups.find_one({'name' : 'group_one'})
			game = mongo.db.games.find_one({'id' : 0})

		self.assertEqual(group['owner'], 'abc@gmail.com')
		self.assertEqual(group['users'], ['abc@gmail.com'])
		self.assertEqual(group['invitees'], ['def@gmail.com', 'ghi@gmail.com'])

		self.assertEqual(response.status_code, 200)
		self.assertTrue("<table id='my_portfolio'" in response.data.decode("utf-8"))

		# test out of date range
		with app.app_context():
			mongo.db.games.update_one(
				{'id': 0},
				{"$set": {'start_date': datetime.datetime.strftime(tomorrow, '%Y-%m-%d')}}
			)
			mongo.db.groups.delete_one({"name": "group_one"})

		response = self.create_group('group_one', 'def@gmail.com,ghi@gmail.com,')
		self.assertEqual(response.status_code, 200)
		self.assertTrue("This is not a current game period." in response.data.decode("utf-8"))

	def test_create_group_exists(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')

		with app.app_context():
			mongo.db.games.insert_one({'id': 1, 'reg_start_date': '2017-11-01', 'reg_end_date': '2017-11-30', 'start_date': '2017-12-07', 'end_date': '2018-05-02'})

		self.create_group('group_one', '')
		self.logout()

		self.register('ghi@gmail.com', 'Hello123', 'Hello123')
		self.login('ghi@gmail.com', 'Hello123')
		response = self.create_group('group_one', '')

		self.assertEqual(response.status_code, 200)
		self.assertTrue("<strong>ERROR:</strong> Group name already exists." in response.data.decode("utf-8"))

	# @patch('pandas_datareader.data.DataReader')
	# @patch('requests.get')
	# def test_search(self, mock_get_a, mock_get_b):
	# 	a_data = {'ResultSet': {'Query': 'goog', 'Result': [{'type': 'S', 'symbol': 'GOOG', 'exch': 'NGM', 'exchDisp': 'NASDAQ', 'name': 'Alphabet Inc.', 'typeDisp': 'Equity'}, {'type': 'S', 'symbol': 'GOOGL', 'exch': 'NMS', 'exchDisp': 'NASDAQ', 'name': 'Alphabet Inc.', 'typeDisp': 'Equity'}, {'type': 'S', 'symbol': 'GOOGL-USD.SW', 'exch': 'EBS', 'exchDisp': 'Swiss', 'name': 'Alphabet', 'typeDisp': 'Equity'}, {'type': 'S', 'symbol': 'GOOG.SN', 'exch': 'SGO', 'exchDisp': 'Santiago Stock Exchange', 'name': 'ALPHABET INC', 'typeDisp': 'Equity'}, {'type': 'S', 'symbol': 'GOOGL.MX', 'exch': 'MEX', 'exchDisp': 'Mexico', 'name': 'Alphabet Inc.', 'typeDisp': 'Equity'}, {'type': 'O', 'symbol': 'GOOGL190621C01500000', 'exch': 'OPR', 'exchDisp': 'OPR', 'name': 'GOOGL Jun 2019 call 1500.000', 'typeDisp': 'Option'}, {'type': 'S', 'symbol': 'GOOGL.SW', 'exch': 'EBS', 'exchDisp': 'Swiss', 'name': 'Alphabet Inc.', 'typeDisp': 'Equity'}, {'type': 'O', 'symbol': 'GOOG171117C00785000', 'exch': 'OPR', 'exchDisp': 'OPR', 'name': 'GOOG Nov 2017 call 785.000', 'typeDisp': 'Option'}, {'type': 'O', 'symbol': 'GOOGL171110C01070000', 'exch': 'OPR', 'exchDisp': 'OPR', 'name': 'GOOGL Nov 2017 call 1070.000', 'typeDisp': 'Option'}, {'type': 'O', 'symbol': 'GOOGL171110C01050000', 'exch': 'OPR', 'exchDisp': 'OPR', 'name': 'GOOGL Nov 2017 call 1050.000', 'typeDisp': 'Option'}]}}
	# 	b_data = [{'date':'2016-11-10', 'Open':778.81, 'Low':728.90, 'High':729.80, 'Close':739.01, 'Volume':6622784},
	# 			  {'date':'2016-11-11', 'Open':778.81, 'Low':728.90, 'High':729.80, 'Close':739.01, 'Volume':6622784}]
	# 	mock_get_a.return_value.json.return_value = a_data
	# 	mock_get_b.return_value = pandas.DataFrame(b_data)
	# 	response = self.app.post('/search', data=dict(search='goog'))
	# 	self.assertEqual(response.status_code, 200)

	def games(self):
		return self.app.get("/games")

	def test_game_registration(self):
		day0 = datetime.date.today()
		day1 = day0 + datetime.timedelta(days=1)
		day2 = day0 + datetime.timedelta(days=2)
		day3 = day0 + datetime.timedelta(days=3)

		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')

		response = self.games()
		self.assertEqual(200, response.status_code)
		self.assertTrue("ERROR: Currently not a registration or a game period" in response.data.decode("utf-8"))

		with app.app_context():
			mongo.db.groups.insert_one({
				'name': 'group_one',
				'stocks': [],
				'total_cost': 1000,
				'money': 100000,
				'users': [],
				'invitees': ['abc@gmail.com', 'def@gmail.com']
			})
			mongo.db.games.insert_one({
				'id': 0,
				'reg_start_date': datetime.datetime.strftime(day0, '%Y-%m-%d'),
				'reg_end_date': datetime.datetime.strftime(day1, '%Y-%m-%d'),
				'start_date': datetime.datetime.strftime(day2, '%Y-%m-%d'),
				'end_date': datetime.datetime.strftime(day3, '%Y-%m-%d'),
				'groups': ['group_one']
			})

		response = self.games()
		self.assertEqual(200, response.status_code)
		self.join_group("group_one")
		response = self.games()
		self.assertTrue("This is not a current game period." in response.data.decode("utf-8"))


	def test_game(self):
		today = datetime.date.today()
		tomorrow = today + datetime.timedelta(days=1)
		reg_start_date = today - datetime.timedelta(days=2)
		reg_end_date = today - datetime.timedelta(days=1)

		# format dates to string
		today = datetime.datetime.strftime(today, '%Y-%m-%d')
		tomorrow = datetime.datetime.strftime(tomorrow, '%Y-%m-%d')
		reg_start_date = datetime.datetime.strftime(reg_start_date, '%Y-%m-%d')
		reg_end_date = datetime.datetime.strftime(reg_end_date, '%Y-%m-%d')

		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')

		with app.app_context():
			mongo.db.groups.insert_one({
				'name': 'group_one',
				'stocks': [],
				'total_cost': 1000,
				'money': 100000,
				'users': []
			})
			mongo.db.games.insert({
				'id': 0,
				'reg_start_date': reg_start_date,
				'reg_end_date': reg_end_date,
				'start_date': today,
				'end_date': tomorrow,
				'groups': ['group_one']
			})

		self.join_group("group_one")
		response = self.games()
		self.assertEqual(200, response.status_code)

		self.add_stock('Google', 'GOOG', "5", "5", "true")
		response = self.games()
		self.assertEqual(200, response.status_code)
		self.assertTrue("GOOG" in response.data.decode('utf-8'))

	def leaderboard(self):
		return self.app.get("/leaderboard")

	def test_leaderboard(self):
		today = datetime.date.today()
		tomorrow = today + datetime.timedelta(days=1)
		reg_start_date = today - datetime.timedelta(days=2)
		reg_end_date = today - datetime.timedelta(days=1)

		# format dates to string
		today = datetime.datetime.strftime(today, '%Y-%m-%d')
		tomorrow = datetime.datetime.strftime(tomorrow, '%Y-%m-%d')
		reg_start_date = datetime.datetime.strftime(reg_start_date, '%Y-%m-%d')
		reg_end_date = datetime.datetime.strftime(reg_end_date, '%Y-%m-%d')

		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login('abc@gmail.com', 'Hello123')

		with app.app_context():
			mongo.db.groups.insert_one({
				'name': 'group_one',
				'stocks': [],
				'total_cost': 1000,
				'money': 1,
				'users': []
			})
			mongo.db.groups.insert_one({
				'name': 'group_two',
				'stocks': [{'price': 0.0, 'market_value': 0.0, 'change_percentage': 0.0, 'change': 0.0, 'gain': 0.0, 'gain_percentage': 0.0, 'name': 'Google', 'cost': 50.0, 'shares': 10, 'ticker': 'GOOG'}],
				'total_cost': 1000,
				'money': 2,
				'users': []
			})
			mongo.db.games.insert_one({
				'id': 0,
				'reg_start_date': reg_start_date,
				'reg_end_date': reg_end_date,
				'start_date': today,
				'end_date': tomorrow,
				'groups': ['group_one']
			})
		response = self.leaderboard()
		loc1 = response.data.decode('utf-8').index("group_one")
		loc2 = response.data.decode('utf-8').index("group_two")
		self.assertTrue(loc2 < loc1)


	def logout(self):
		return self.app.post('/logout')

	def test_logout(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login("abc@gmail.com", "Hello123")
		response = self.logout()
		self.assertEqual(response.status_code, 302)

	def test_stock_info(self):
		info = updater.stock_info('GOOG')
		self.assertEqual(len(info),6)
		assert type(info[0]) is float
		assert type(info[1]) is float
		assert type(info[2]) is float
		assert type(info[3]) is float
		assert type(info[4]) is float
		assert type(info[5]) is str

	def test_get_close(self):
		close = updater.get_close('GOOG')
		assert type(close) is float

	def test_get_info(self):
		info = updater.get_info('GOOG')
		self.assertEqual(len(info), 5)
		assert type(info[0]) is float
		assert type(info[1]) is float
		assert type(info[2]) is float
		assert type(info[3]) is float
		assert type(info[4]) is str

	def test_ordered_time_series(self):
		data = updater.ordered_daily_time_series_full('GOOG')
		for info in data:
			self.assertEqual(len(info),6)
			assert type(info[0]) is str
			assert type(info[1]) is float
			assert type(info[2]) is float
			assert type(info[3]) is float
			assert type(info[4]) is float
			assert type(info[5]) is float

	def test_scheduler(self):
		stock_stub = {
			"price" : 1.,
			"low_price" : 1.,
			"open_price" : 1.,
			"high_price" : 1.,
			"close_price" : 1.,
			"ticker" : "GOOG",
			"volume" : "0"
		}

		with app.app_context():
			mongo.db.stocks.delete_many({})
			mongo.db.stocks.insert_one(stock_stub)

		updater.update()

		with app.app_context():
			stock = mongo.db.stocks.find_one({'ticker' : "GOOG"})

		self.assertTrue(stock != stock_stub)

	def test_updater_add_stock(self):
		with app.app_context():
			mongo.db.stocks.delete_many({})

		updater.add_stock("GOOG", 1000.0)
		with app.app_context():
			for stock in mongo.db.stocks.find({}):
				if stock["ticker"] == "GOOG":
					assert True

	def test_search(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login("abc@gmail.com", "Hello123")
			
		response_1 = self.app.post('/search', data=dict(search='goog'))
		self.assertEqual(response_1.status_code, 200)
		self.assertEqual("GOOG" in response_1.data.decode("utf-8"), True)
		
		response_2 = self.app.post('/search', data=dict(search='rubbish'))
		self.assertEqual(response_2.status_code, 200)
		self.assertEqual("ERROR: invalid ticker" in response_2.data.decode("utf-8"), True)

		# ingame case
		with app.app_context():
			mongo.db.groups.insert_one({'name': 'group_one', 'stocks': [], 'total_cost': 1000, 'money':1000})
			mongo.db.games.insert_one({'id': 0, 'reg_start_date': '2017-11-01', 'reg_end_date': '2017-11-30', 'start_date': '2017-12-07', 'end_date': '2018-05-02'})

		self.join_group('group_one')
		response_3 = self.app.post('/search', data=dict(search='goog'))
		self.assertEqual(response_3.status_code, 200)
		self.assertTrue("<h4>Add Stock to Game Portfolio</h4>" in response_3.data.decode("utf-8"))


# if __name__ == '__main__':
# 	unittest.main()












	
