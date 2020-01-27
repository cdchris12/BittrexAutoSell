#!/usr/bin/env python3

import sys
import os.path
import json
import hashlib
import hmac
import base64
import requests as r
import arrow

if not os.path.exists("config.json"):
    sys.exit(
        """
        No config file found!
        Please ensure \"config.json\" exists and is readable!
        """
    )
# End if

with open("config.json", "r") as infile:
    config = json.load(infile)
    try:
        assert config.get("APIToken","") != ""
        assert config.get("FinalCoin","") != ""
    except:
        sys.exit(
        """
        The \"config.json\" file exists, but is missing data.
        Please verify this file contains a value for \"APIToken\" and \"FinalCoin\"
        """
        )
    # End try/except
# End with

def getMarkets():
    """
    Make an unatuhenticated call to the Bittrex API to get a list
      of all supported markets
    """
    res = r.get("https://api.bittrex.com/api/v1.1/public/getmarkets")
    res.raise_for_status()

    return res.json()
# End def

def getTickerValues(Market):
    """
    Make an unauthenticated call to get the current ticket values
      for a specified market
    """
    res = r.get("https://api.bittrex.com/api/v1.1/public/getticker?market=%s" % Market)
    res.raise_for_status()

    return res.json()
# End def

def filterMarkets(walletCoins, markets):
    """
    Filter the list of all markets to only contain markets relevant to the
      coins we hold balances in
    """
    coinsWithBalances = []
    monitoredMarkets = []

    for wallet in walletCoins:
        if wallet["Balance"] > 0.0:
            coinsWithBalances.append(wallet["Currency"])
        # End if
    # End for

    for market in markets:
        if market["MarketCurrency"] in coinsWithBalances:
            monitoredMarkets.append(market)
        # End if
    # End for

    return monitoredMarkets
# End def

def getBalances(APIToken, IgnoredCoins=[]):
    """
    Hit the Bittrex API to get a list of coin wallets with balances.
    Filter any ignored coins from that list
    Iterate over each remaining coin (if any) and process sell orders
      for those coins
    
    Example API return data:
    {
      "success": true,
      "message": "''",
      "result": [
        {
          "Currency": "DOGE",
          "Balance": 4.21549076,
          "Available": 4.21549076,
          "Pending": 0,
          "CryptoAddress": "DLxcEt3AatMyr2NTatzjsfHNoB9NT62HiF",
          "Requested": false,
          "Uuid": null
        }
      ]
    }

    This function will return data as a list of dicts:
    [
      {
        "Currency": "DOGE",
        "Balance": 4.21549076,
        "Available": 4.21549076,
        "Pending": 0,
        "CryptoAddress": "DLxcEt3AatMyr2NTatzjsfHNoB9NT62HiF",
        "Requested": false,
        "Uuid": null
      }
    ]

    """
    res = r.get("https://api.bittrex.com/api/v1.1/account/getbalances?apikey=%s" % APIToken)
    res.raise_for_status
    output = res.json()["result"]

    balances = []

    for crypto in output:
        if IgnoredCoins and crypto["Currency"] not in IgnoredCoins:
            balances.append(output[crypto])
        # End if
    # End for

    return balances
# End def

def sellCoin(APIToken, APISecret, SourceCoin, DestCoin, Markets):
    """
    APIToken: String
    APISecret: String
    SourceCoin: coin object
    DestCoin: String
    Markets: List of market objects
    """

    def _sell(API_Token, APISecret, Market, Balance):
        """
        This will post a "MARKET" order, which should be immediately filled at whatever market rate is.
        """

        data = {
          "marketSymbol": Market["MarketName"],
          "direction": "SELL",
          "type": "MARKET",
          "quantity": Balance,
          "timeInForce": "FILL_OR_KILL",
        }
        ts = arrow.now().timestamp * 1000 # Transforms ts from seconds into milliseconds
        uri = "https://api.bittrex.com/v3/orders"
        contentHash, signature = generateAuth(API_Token, APISecret, ts, str(data), uri, "POST")

        headers = {
            "Api-Key": API_Token,
            "Api-Timestamp": ts;
            "Api-Content-Hash": contentHash;
            "Api-Signature": signature
        }

        r = requests.post(uri, data=data, headers=headers)
        r.raise_for_status()

        res = r.json()
        return res["id"]
    # End def

    def _checkOrder(API_Token, APISecret, UUID):
        """
        Returns true/false based on whether an order needs to be retried
        """

        ts = arrow.now().timestamp * 1000 # Transforms ts from seconds into milliseconds
        uri = "https://api.bittrex.com/v3/orders/%s" % UUID
        contentHash, signature = generateAuth(API_Token, APISecret, ts, "", uri, "GET")

        headers = {
            "Api-Key": API_Token,
            "Api-Timestamp": ts;
            "Api-Content-Hash": contentHash;
            "Api-Signature": signature
        }

        r = requests.get(uri, headers=headers)
        r.raise_for_status()

        res = r.json()

        if res["quantity"] != res['fillQuantity']:
            # Order didn't completely fill; need to signal that the rest should be sold somehow
            #TODO
            return True
        elif res['fillQuantity'] == 0.0:
            # Order was not filled at all; needs to be reattempted immediately
            return False
        else:
            # Order filled completely
            #TODO include timestamp and market in this logging message
            print("Order filled successfully!")
            return True
        # End if/else block
    # End def

    sellMarkets = []

    # First, check to see if direct market exists, for example "USDT-GRIN"
    for market in markets:
        if market["MarketName"] == "%s-%s" % (DestCoin, SourceCoin):
            sellMarkets.append(market)
        # End if
    # End for

    # If direct market doesn's exist, then we need to sell SourceCoin for BTC first and then sell BTC for DestCoin
    if not sellMarkets:
        for market in markets:
            if market["MarketName"] == "%s-%s" % ("BTC", SourceCoin):
                sellMarkets.append(market)
            # End if
        # End for

        for market in markets:
            if market["MarketName"] == "%s-%s" % ("BTC", DestCoin):
                sellMarkets.append(market)
            # End if
        # End for
    # End if

    for market in sellMarkets:
        completed = False
        while not completed:
            uuid = _sell(APIToken, APISecret, market, SourceCoin["Available"])
            completed = _checkOrder(APIToken, APISecret, uuid)
        # End while
    # End for
# End def

def generateAuth(APIToken, APISecret, Timestamp, ContentToHash, URI, HTTPMethod, Subaccount_ID=""):
    """
    To test hashing functions in JS:
      var CryptoJS = require("crypto-js");
      var contentHash = CryptoJS.SHA512("{'abc': 123}").toString(CryptoJS.enc.Hex);
      contentHash;
    """
    assert type(ContentToHash) == type("") # Our content should be a string
    hashedContent = hashlib.sha512(ContentToHash.encode('utf-8')).hexdigest()

    # Signature requires:
    # Timestamp + URI + Method + hashedContent + Subaccount_ID
    msg = """%s%s%s%s%s""" % (Timestamp, URI, HTTPMethod, hashedContent, Subaccount_ID)
    digest = hmac.new(APISecret.encode(), msg=msg.encode(), digestmod=hashlib.sha512).hexdigest()

    return (hashedContent, digest)
# End def

def main():
    # Load config data
    APIToken = config["APIToken"]
    APISecret = config["APISecret"]
    FinalCoin = config["FinalCoin"]
    IgnoredCoins = config.get("IgnoredCoins",[])

    # Get list of available markets
    markets = getmarkets()

    # Get list of coins to be sold
    coinsToSell = getBalances(APIToken, IgnoredCoins)

    # Filter list of all available markets to only contain relevant markets
    relevantMarkets = filterMarkets(coinsToSell, markets)
    
    # Sell any coins that need to be sold
    for coin in coinsToSell:
        sellCoin(APIToken, APISecret, coin, FinalCoin, relevantMarkets)
    # End for
# End def

if __name__ == "__main__" :
    main()
# End if