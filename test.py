import pytest
from server import *

import unittest


TEST_DB = 'test.db'

class MarketGameTests(unittest.TestCase):
	def setUp(self):
		app.secret_key = 'super secret key'
		app.config['TESTING'] = True
		app.config['MONGODB_DATABASE'] = 'test'
		self.app = app.test_client()

	def tearDown(self):
		pass

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
		response = self.register('abc@gmail.com', 'hello', 'hello')
		self.assertEqual(response.status_code, 200)

	def login(self, username, password):
		return self.app.post('/login', data=dict(username=username, password=password.encode('utf-8')), follow_redirects=True)

	def test_login(self):
		response = self.login('abc@gmail.com', 'hello')
		self.assertEqual(response.status_code, 200)

	def add_stock(self, ticker, date, shares, price, commission):
		return self.app.post('/add_stock', data=dict(ticker=ticker, date=date, shares=shares, price=price, commission=commission), follow_redirects=True)

	def test_add_stock(self):
		self.login("abc@gmail.com", "hello")
		response = self.add_stock('GOOG', '1/1/2017', "50", "200", "50")
		self.assertEqual(response.status_code,200)








	
