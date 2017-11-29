
import requests
import sched, time
from bs4 import BeautifulSoup
from pymongo import MongoClient

def get_price(ticker):
	"""
	Peeks at the current price of the stock
	"""
	result = requests.get("https://finance.google.com/finance?q=" + ticker)
	soup = BeautifulSoup(result.content, "lxml")
	return float(soup.find("span", {"class": "pr"}).find("span").text)

def scrape(ticker, peek=False):
	"""
	:Input:
	 - ticker (string): stock ticker to collect information about
	 - peek (boolean): if peek, then return a tuple of information from the
	  	previous day

	:Output:
	IF PEEK
	 - (tuple): open_price, high_price, low_price, close_price, volume
	ELSE
	 - (list): closing prices for the last 200 days

	price, close_price, open_price, low_price, high_price, volume, ordered_daily_time_series_full
	"""
	result = requests.get("https://finance.google.com/finance/historical?q=" + ticker + "&num=200")
	soup = BeautifulSoup(result.content, "lxml")
	table = soup.find("table", {"class": "historical_price"})
	if peek:
		return table.find("tr", {"class": ""}).find_all("td")[1:]
	

def update(s):
	print("1")
	client = MongoClient()
	db = client.winydb

	# Update portfolios for each user
	users = db.users

	# One-way associative cache
	cache = {}

	for user in users.find():
		print(user)
		for stock in user["stocks"]:
			if (stock["ticker"] in cache):
				users.update_one({"name": user["name"], "stocks.ticker": stock["ticker"]}, {
					"$set": {
						"stocks.$.price": cache[stock["ticker"]]
					}
				})
				continue

			price = get_price(stock["ticker"])
			users.update_one({"name": user["name"], "stocks.ticker": stock["ticker"]}, {
				"$set": {
					"stocks.$.price": price
				}
			})
			cache[stock["ticker"]] = price

	# Update portfolios for each group
	groups = db.groups
	for group in groups.find():
		for stock in group["stocks"]:
			if (stock["ticker"] in cache):
				groups.update_one({"name": group["name"], "stocks.ticker": stock["ticker"]}, {
					"$set": {
						"stocks.$.price": cache[stock["ticker"]]
					}
				})
				continue

			price = get_price(stock["ticker"])
			groups.update_one({"name": group["name"], "stocks.ticker": stock["ticker"]}, {
				"$set": {
					"stocks.$.price": price
				}
			})
			cache[stock["ticker"]] = price

	# repeat in 15 minutes
	s.enter(900, 1, update, (s,))

def main():
	# Create a scheduler
	s = sched.scheduler(time.time, time.sleep)
	s.enter(900, 1, update, (s,))
	s.run()

if __name__ == "__main__":
	main()