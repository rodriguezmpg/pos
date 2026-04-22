import requests
import json

# Configura el símbolo que deseas filtrar (ejemplo: 'ETHUSDT')
symbol = "CRVUSDT"

# Obtiene el exchangeInfo completo
url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
data = requests.get(url).json()

# Busca el diccionario del símbolo indicado
symbol_info = next((s for s in data['symbols'] if s['symbol'] == symbol), None)

if symbol_info:
    print(json.dumps(symbol_info, indent=4))
else:
    print(f"No se encontró información para el símbolo {symbol}")

