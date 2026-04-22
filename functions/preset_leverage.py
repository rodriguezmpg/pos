import os
from binance.client import Client
from dotenv import load_dotenv


'''
ESTE CODIGO DEJA PREDEFINIDO EL APALANCAMIENTO MAXIMO EN CADA SIMBOLO, LO DEBERIA VOLVER A EJECUTAR SI QUIERO COMPROBAR
SI BINANCE CAMBIO EL APALANCAAMIENTO DE ALGUNO.

'''

load_dotenv()

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
client = Client(API_KEY, API_SECRET, tld='com')

symbols = [
    "ETHUSDT", "BTCUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "TRXUSDT", "AVAXUSDT",
    "TONUSDT", "LTCUSDT", "1000SHIBUSDT", "DOGEUSDT", "ADAUSDT", "XLMUSDT",
    "XMRUSDT", "DOTUSDT", "UNIUSDT", "APTUSDT", "NEARUSDT", "FETUSDT",
    "ARBUSDT", "HYPERUSDT", "SUIUSDT", "BCHUSDT", "LINKUSDT", "HBARUSDT",
    "1000PEPEUSDT", "AAVEUSDT", "TAOUSDT", "ICPUSDT", "ETCUSDT",
    "ONDOUSDT", "KASUSDT", "ATOMUSDT", "VETUSDT", "RENDERUSDT", "ENAUSDT",
    "FILUSDT", "WLDUSDT", "ALGOUSDT", "QNTUSDT", "SEIUSDT", "JUPUSDT",
    "SPXUSDT", "INJUSDT", "TIAUSDT", "VIRTUALUSDT", "STXUSDT", "OPUSDT",
    "PENGUUSDT", "IOTAUSDT", "IMXUSDT", "GRTUSDT", "IPUSDT", "CAKEUSDT",
    "JTOUSDT", "CRVUSDT", "THETAUSDT", "LDOUSDT", "GALAUSDT", "ZECUSDT"
]

for symbol in symbols:
    try:
        brackets = client.futures_leverage_bracket(symbol=symbol)
        max_leverage = brackets[0]['brackets'][0]['initialLeverage']
        client.futures_change_leverage(symbol=symbol, leverage=max_leverage)
        print(f"{symbol}: apalancamiento seteado a {max_leverage}x")
    except Exception as e:
        print(f"{symbol}: ERROR - {e}")