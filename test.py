import pytest
from server import *
import pandas
import unittest
from unittest.mock import patch
import flask_pymongo
import updater
# import flask
# from flask import session

TEST_DB = 'new_test.db'


class MarketGameTests(unittest.TestCase):
	def setUp(self):
		app.secret_key = 'super secret key'
		app.config['TESTING'] = True
		app.config['MONGODB_DATABASE'] = 'new_test'
		self.app = app.test_client()

	def tearDown(self):
		with app.app_context():
			mongo.db.users.remove({})



###############
#### tests ####
###############

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

		if not found:
			assert False

		response_4 = self.add_stock('Apple', 'AAPL', "", "5", "false")
		self.assertEqual(response_4.status_code, 302)
		for stock in stocks:
			if stock['ticker'] == 'AAPL':
				assert False

		response_5 = self.add_stock('Facebook', 'FB', "5", "5", "false")
		response_6 = self.add_stock('Facebook', 'FB', "-5", "5", "false")
		self.assertEqual(response_5.status_code, 302)
		self.assertEqual(response_6.status_code, 302)
		for stock in stocks:
			if stock['ticker'] == 'FB':
				print("WTF")
				print(stock['ticker'])
				print(stock["shares"])
				assert False
			
			

	def test_profile(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login("abc@gmail.com", "Hello123")
		response_1 = self.add_stock('Google', 'GOOG', "5", "5", "false")
		self.assertEqual(response_1.status_code, 302)

		response_2 = self.app.get("/profile")
		self.assertEqual(response_2.status_code, 200)
		self.assertEqual("<td>GOOG</td>" in response_2.data.decode("utf-8"), True)



	def test_search(self):
		self.register('abc@gmail.com', 'Hello123', 'Hello123')
		self.login("abc@gmail.com", "Hello123")




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


if __name__ == '__main__':
	unittest.main()












	
