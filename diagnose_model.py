#!/usr/bin/env python
import pandas as pd
from binance_http_client import BinanceFuturesHTTP
import os
import joblib
from feature_generator import generate_features

symbol = 'BTC/USDT'
print('Fetching klines...')
client = BinanceFuturesHTTP(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'), testnet=True)
ohlcv = client.fetch_klines('BTCUSDT','5m', limit=500)
df = pd.DataFrame(ohlcv)
if df.shape[1] >=6:
    df = df.iloc[:,:6]
    df.columns = ['timestamp','open','high','low','close','volume']
    df['date']=pd.to_datetime(df['timestamp'],unit='ms')
    df.set_index('date', inplace=True)

print('Generating features...')
features_df = generate_features(df.copy())
features_df.dropna(inplace=True)
if features_df.empty:
    print('Features are empty after dropna. Cannot diagnose.')
    raise SystemExit(1)

safe_ticker = symbol.replace('/','_').upper()
model_path = f'./{safe_ticker}_model.joblib'
print('Loading model:', model_path)
m = joblib.load(model_path)

if hasattr(m,'feature_names_in_'):
    model_features = list(m.feature_names_in_)
else:
    # fallback feature list (must match model expectation)
    model_features = [c for c in features_df.columns if c not in ['open','high','low','close','volume','date']]

missing = [f for f in model_features if f not in features_df.columns]
print('Missing features:', missing)
last_day = features_df.iloc[-1:][model_features]
prediction = m.predict(last_day)[0]
print('\nPrediction:', prediction)
print('Signal mapping: >0.005 BUY, < -0.005 SELL')
if prediction > 0.005:
    print('=> BUY')
elif prediction < -0.005:
    print('=> SELL')
else:
    print('=> HOLD')

print('\nLast day feature vector (first 40 chars):')
print(last_day.to_dict())

print('\nModel type:', type(m))
if hasattr(m,'feature_importances_'):
    fi = sorted(list(zip(model_features, m.feature_importances_)), key=lambda x:-x[1])[:15]
    print('\nTop feature importances:')
    for name,imp in fi:
        print(name, imp)
else:
    coef = getattr(m, 'coef_', None)
    if coef is not None:
        print('\nModel coefficients (length):', len(coef))
else:
    try:
        coef = getattr(m, 'coef_', None)
        if coef is not None:
            print('\nModel coefficients (first 10):', coef[:10])
    except Exception:
        pass
