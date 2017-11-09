import pytest
from server import *
import pandas
import unittest
from unittest.mock import patch


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
		return self.app.post('/login', data=dict(username=username, password=password.encode('ascii')), follow_redirects=True)

	def test_login(self):
		response = self.login('abc@gmail.com', 'hello')
		self.assertEqual(response.status_code, 200)

	def add_stock(self, ticker, date, shares, price, commission):
		return self.app.post('/add_stock', data=dict(ticker=ticker, date=date, shares=shares, price=price, commission=commission), follow_redirects=True)

	def test_add_stock(self):
		self.login("abc@gmail.com", "hello")
		response = self.add_stock('GOOG', '1/1/2017', "50", "200", "50")
		self.assertEqual(response.status_code,200)

	@patch('pandas_datareader.data.DataReader')
	@patch('requests.get')
	def test_search(self, mock_get_a, mock_get_b):
		a_data = {'ResultSet': {'Query': 'goog', 'Result': [{'type': 'S', 'symbol': 'GOOG', 'exch': 'NGM', 'exchDisp': 'NASDAQ', 'name': 'Alphabet Inc.', 'typeDisp': 'Equity'}, {'type': 'S', 'symbol': 'GOOGL', 'exch': 'NMS', 'exchDisp': 'NASDAQ', 'name': 'Alphabet Inc.', 'typeDisp': 'Equity'}, {'type': 'S', 'symbol': 'GOOGL-USD.SW', 'exch': 'EBS', 'exchDisp': 'Swiss', 'name': 'Alphabet', 'typeDisp': 'Equity'}, {'type': 'S', 'symbol': 'GOOG.SN', 'exch': 'SGO', 'exchDisp': 'Santiago Stock Exchange', 'name': 'ALPHABET INC', 'typeDisp': 'Equity'}, {'type': 'S', 'symbol': 'GOOGL.MX', 'exch': 'MEX', 'exchDisp': 'Mexico', 'name': 'Alphabet Inc.', 'typeDisp': 'Equity'}, {'type': 'O', 'symbol': 'GOOGL190621C01500000', 'exch': 'OPR', 'exchDisp': 'OPR', 'name': 'GOOGL Jun 2019 call 1500.000', 'typeDisp': 'Option'}, {'type': 'S', 'symbol': 'GOOGL.SW', 'exch': 'EBS', 'exchDisp': 'Swiss', 'name': 'Alphabet Inc.', 'typeDisp': 'Equity'}, {'type': 'O', 'symbol': 'GOOG171117C00785000', 'exch': 'OPR', 'exchDisp': 'OPR', 'name': 'GOOG Nov 2017 call 785.000', 'typeDisp': 'Option'}, {'type': 'O', 'symbol': 'GOOGL171110C01070000', 'exch': 'OPR', 'exchDisp': 'OPR', 'name': 'GOOGL Nov 2017 call 1070.000', 'typeDisp': 'Option'}, {'type': 'O', 'symbol': 'GOOGL171110C01050000', 'exch': 'OPR', 'exchDisp': 'OPR', 'name': 'GOOGL Nov 2017 call 1050.000', 'typeDisp': 'Option'}]}}
		b_data = [{'date':'2016-11-10', 'Open':778.81, 'Low':728.90, 'High':729.80, 'Close':739.01, 'Volume':6622784}]
		mock_get_a.return_value.json.return_value = a_data
		mock_get_b.return_value = pandas.DataFrame(b_data)
		response = self.app.post('/search', data=dict(search='goog'))
		self.assertEqual(response.status_code,200)












	
