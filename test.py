import pytest
from server import *
from flask import current_app
import unittest


TEST_DB = 'test.db'

class MarketGameTests(unittest.TestCase):
	def setup(self):
		app.config['MONGODB_DATABASE'] = 'test'
		self.app = app.test_client()
	def tearDown(self):
		connection.test.drop_collection('mycollection')

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






	