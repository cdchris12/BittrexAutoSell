#!/usr/bin/env python3

import sys
import os.path
import json
import requests as r

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

def sellCoin(APIToken, SourceCoin, DestCoin, Markets):
    """
    First, determine if a coin can be directly sold from the source
      crypto into the dest crypto
    If it can, then call _Sell to actually sell the crypto
    If not, then process the crypto's sale into BTC first, then dest
      crypto afterwards via two calls to _Sell
    """

    # Call the API to see if Src->Dest market exists
    #  If yes: 
    #    Call _Sell(APIToken=APIToken, Src=SourceCoin, Dest=DestCoin)
    #  If no:
    #    Call _Sell(APIToken=APIToken, Src=SourceCoin, Dest="BTC")
    #    Call _Sell(APIToken=APIToken, Src="BTC", Dest=DestCoin)
    pass
# End def

def main():
    # Load config data
    APIToken = config["APIToken"]
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
        sellCoin(APIToken, coin, FinalCoin, relevantMarkets)
    # End for
# End def

if __name__ == "__main__" :
    main()
# End if