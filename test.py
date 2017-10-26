import pytest
from server import *

import unittest


TEST_DB = 'test.db'

class MarketGameTests(unittest.TestCase):
	def setup(self):
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
		return self.app.post('/login', data=dict(username=username, password=password), follow_redirects=True)

	def check_login():
		response = self.login('abc@gmail.com', 'hello')
		self.assertEqual(response.status_code,200)






	