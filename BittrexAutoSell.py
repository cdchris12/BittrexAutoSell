#!/usr/bin/python3

import requests as r


def getBalances(APIToken="", IgnoredCoins=[]):
    """
    Hit the Bittrex API to get a list of coin wallets with balances.
    Filter any ignored coins from that list
    Iterate over each remaining coin (if any) and process sell orders
      for those coins
    """
    pass
# End def

def sellCoin(APIToken="", SourceCoin="", DestCoin=""):
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
    pass
# End def

if __name__ == "__main__" :
    main()
# End if