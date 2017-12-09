
import requests
import sched
import time
import re
from bs4 import BeautifulSoup
from pymongo import MongoClient


def get_close(ticker):
	result = requests.get("https://finance.google.com/finance/historical?q=" + ticker + "&num=200")
	soup = BeautifulSoup(result.content, "lxml")
	table = soup.find("table", {"class": "historical_price"})
	return float(table.find("tr", {"class": ""}).find_all("td")[4].text.replace(',', ''))

def get_info(ticker):
	result = requests.get("https://finance.google.com/finance?q=" + ticker)
	soup = BeautifulSoup(result.content, "lxml")
	price = float(soup.find("span", {"class": "pr"}).find("span").text.replace(',', ''))
	data = soup.find_all("td", {"class": "val"})
	low, high = data[0].text.split(" - ")
	low = float(low.replace(',', ''))
	high = float(high.replace(',', ''))
	open_price = float(data[2].text.replace(',', ''))
	volume = data[3].text.split("/")[0]

	return price, low, high, open_price, volume

def add_stock(ticker, close_price):
	client = MongoClient()
	db = client.winydb

	stocks = db.stocks
	if stocks.find_one({"ticker": ticker}) == None:
		price, low, high, open_price, volume = get_info(ticker)
		# close_price = get_close(stock["ticker"])
		stocks.insert_one({
					"ticker": ticker,
					"price": price,
					"low_price": low,
					"high_price": high,
					"open_price": open_price,
					"close_price": close_price,
					"volume": volume
		})

def stock_info(ticker):
	client = MongoClient()
	db = client.winydb
	info = db.stocks.find_one({"ticker": ticker})

	# If we cannot find info, add the stock to the db, and try again
	if info == None:
		close_price = get_close(ticker)
		add_stock(ticker, close_price)
		return stock_info(ticker)
	#close_price, previous_close_price, open_price, low_price, high_price, volume
	return info["price"], info["close_price"], info["open_price"], info["low_price"], info["high_price"], info["volume"]

def update_stocks(s):
	print("[" + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + "]: Updating...")
	client = MongoClient()
	db = client.winydb

	# Update the stocks
	stocks = db.stocks
	for stock in stocks.find():
		price, low, high, open_price, volume = get_info(stock["ticker"])
		close_price = get_close(stock["ticker"])

		# Update each value
		stocks.update_one(
			{"ticker": stock["ticker"]},
			{"$set": {
					"price": price,
					"low_price": low,
					"high_price": high,
					"open_price": open_price,
					"close_price": close_price,
					"volume": volume
				}
			}
		)

	# repeat in 15 minutes
	s.enter(300, 1, update_stocks, (s,))


def ordered_daily_time_series_full(ticker):
	"""
	:Output:
	 - (list) List of tuples of the form:
	 	(Date, Open, High, Low, Close, Volume)
	"""
	result = requests.get("https://finance.google.com/finance/historical?q=" + ticker + "&num=200")
	soup = BeautifulSoup(result.content, "lxml")
	table = soup.find("table", {"class": "historical_price"})
	data = []
	for row in table.find_all("tr", {"class": ""}):
		cells = row.find_all("td")
		row = [cell.text for cell in row.find_all("td")]
		data.append((cells[0].text.strip(),
					float(cells[1].text.replace(',', '')),
					float(cells[2].text.replace(',', '')),
					float(cells[3].text.replace(',', '')),
					float(cells[4].text.replace(',', '')),
					float(cells[5].text.replace(',', ''))
				))
	return data


if __name__ == "__main__":
	# Create a scheduler
	s = sched.scheduler(time.time, time.sleep)
	s.enter(0, 1, update_stocks, (s,))
	s.run()
