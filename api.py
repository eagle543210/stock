import os
import sys
import platform
import json
import asyncio
import functools
import datetime
import uuid
import joblib
import subprocess
from collections import deque
from typing import List, Dict, Any

import pandas as pd
import numpy as np
import socketio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

# --- Local Modules ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from services.model_service import generate_signal_from_data
from services.trading_service import BinanceTradingService
from services.data_service import write_trade_audit, replace_nan_with_none

# Legacy imports
try:
    import MetaTrader5 as mt5
except Exception:
    mt5 = None

from data_handler import get_any_stock_data
from feature_generator import generate_features
from model_trainer import create_target_labels
from backtester import Backtester
from stock_diagnoser import diagnose_stock
from trader import Trader
try:
    from sklearn.ensemble import RandomForestRegressor
except ImportError:
    pass

# --- Initialization ---
load_dotenv()
app = FastAPI()

# --- Socket.IO ---
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=[], logger=True, engineio_logger=True)
app.mount('/socket.io', socketio.ASGIApp(sio))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global State ---
signal_logs = deque(maxlen=config.SIGNAL_LOG_MAX_LEN)
trader = Trader()
binance_service = BinanceTradingService()

# --- Pydantic Models ---
class TickerInfo(BaseModel):
    ticker: str
    timeframe: str = 'H1'

class TrainRequest(BaseModel):
    ticker: str

class StrategyConfig(BaseModel):
    ticker: str = '600519'
    train_start_date: str = '20180101'
    train_end_date: str = '20221231'
    backtest_start_date: str = '20230101'
    backtest_end_date: str = '20231231'
    initial_capital: float = 100000.0
    future_days: int = 5
    external_event: int = 0
    fundamental_factors: List[str] = []

# --- Helper Functions ---
def add_global_log(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    signal_logs.appendleft(log_entry)

# --- Events ---
@app.on_event("startup")
async def startup_event():
    print("API Startup...")
    if platform.system() == "Windows":
        try:
            if mt5 and mt5.initialize():
                 print("✅ MT5 initialized.")
            else:
                 print("❌ MT5 failed to initialize.")
        except Exception as e:
            print(f"❌ MT5 Init Exception: {e}")
    
    try:
        await binance_service.ensure_markets()
    except Exception as e:
        print(f"❌ Binance Init Warning: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if platform.system() == "Windows" and mt5:
        mt5.shutdown()
    await binance_service.close()

# --- Core Logic (Strategy) ---
# Keeping this here to avoid breaking dependencies in short term
def run_strategy_pipeline(config: StrategyConfig) -> Dict[str, Any]:
    safe_ticker_upper = config.ticker.replace('/', '_').upper()
    MODEL_PATH = config.ticker + '_model.joblib' # Using config ticker for naming to match existing expectations if any
    # Correction: Use config.get_model_path if possible, or consistent naming.
    # Original logic: safe_ticker_upper + _model.joblib
    MODEL_PATH = f'./{safe_ticker_upper}_model.joblib'

    print(f"为股票 {safe_ticker_upper} 准备数据...")
    raw_data_train = get_any_stock_data(ticker=safe_ticker_upper, start_date=config.train_start_date, end_date=config.train_end_date)
    if raw_data_train.empty:
        raise HTTPException(status_code=400, detail="无法获取训练数据")

    raw_data_train['external_event'] = 0
    print("正在生成技术指标特征...")
    data_with_features_train, _ = generate_features(raw_data_train.copy())
    if data_with_features_train.empty:
        raise HTTPException(status_code=400, detail="生成训练特征失败")

    print("正在创建目标标签...")
    data_with_target_train = create_target_labels(data_with_features_train.copy(), future_days=config.future_days)
    if data_with_target_train.empty:
        raise HTTPException(status_code=400, detail="创建目标标签失败")

    target_column_name = f'future_{config.future_days}d_return'
    exclude_cols = [
        'open', 'high', 'low', 'close', 'volume', 'turnover', 'amplitude', 
        'change_pct', 'change_amt', 'turnover_rate', target_column_name, 
        'date', 'code'
    ]
    features_to_use = [col for col in data_with_target_train.columns if col not in exclude_cols and 'future' not in col]
    
    if 'external_event' not in features_to_use:
        features_to_use.append('external_event')

    print(f"将使用以下特征进行训练: {features_to_use}")
    X_train = data_with_target_train[features_to_use]
    y_train = data_with_target_train[target_column_name]

    train_data = pd.concat([X_train, y_train], axis=1).dropna()
    X_train = train_data[features_to_use]
    y_train = train_data[target_column_name]

    if X_train.empty or y_train.empty:
        raise HTTPException(status_code=400, detail="数据处理后没有可用于训练的样本。")

    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    joblib.dump(model, MODEL_PATH)
    print(f"模型训练并保存完成: {MODEL_PATH}")

    importances = model.feature_importances_
    feature_importance_data = sorted(zip(features_to_use, importances), key=lambda x: x[1], reverse=True)

    print(f"在样本外数据上进行回测...")
    raw_data_backtest = get_any_stock_data(ticker=safe_ticker_upper, start_date=config.backtest_start_date, end_date=config.backtest_end_date)
    
    metrics, kline_data, buy_signals, sell_signals = {}, [], [], []
    
    if not raw_data_backtest.empty:
        raw_data_backtest['external_event'] = 0
        data_for_backtest, _ = generate_features(raw_data_backtest.copy())
        if not data_for_backtest.empty:
            backtest_features_to_use = [f for f in features_to_use if f in data_for_backtest.columns]
            if backtest_features_to_use:
                backtester = Backtester(data=data_for_backtest, model_path=MODEL_PATH, features=backtest_features_to_use, initial_capital=config.initial_capital)
                backtester.run_backtest()
                metrics = backtester.get_performance_metrics()
                
                ohlc_data = data_for_backtest[['open', 'close', 'low', 'high']].reset_index()
                ohlc_data.rename(columns={'index': 'date'}, inplace=True)
                ohlc_data['date'] = pd.to_datetime(ohlc_data['date']).dt.strftime('%Y-%m-%d')
                kline_data = ohlc_data.values.tolist()
                
                buy_signals = [[trade['date'].strftime('%Y-%m-%d'), trade['price']] for trade in backtester.trades if trade['type'] == 'BUY']
                sell_signals = [[trade['date'].strftime('%Y-%m-%d'), trade['price']] for trade in backtester.trades if trade['type'] == 'SELL']

    print(f"根据最新数据预测 {config.future_days} 个交易日后的情况...")
    last_day_features_df = data_with_features_train.iloc[-1:][features_to_use].copy()
    last_day_features_df['external_event'] = config.external_event
    
    predicted_return = model.predict(last_day_features_df[features_to_use])[0]
    
    prediction_signal = "持仓"
    if predicted_return > 0.005: 
        prediction_signal = "看涨"
    elif predicted_return < -0.005:
        prediction_signal = "看跌"

    last_close_price = data_with_features_train['close'].iloc[-1]
    predicted_price = last_close_price * (1 + predicted_return)
    
    if not isinstance(data_with_features_train.index, pd.DatetimeIndex):
        data_with_features_train.index = pd.to_datetime(data_with_features_train.index)
    last_trading_date = data_with_features_train.index[-1]
    predicted_date = (last_trading_date + pd.Timedelta(days=config.future_days)).strftime('%Y-%m-%d')

    results = {
        "metrics": metrics,
        "kline_data": kline_data,
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "feature_importance": feature_importance_data,
        "next_day_prediction": {
            "date": predicted_date,
            "signal": prediction_signal,
            "predicted_price": f"{predicted_price:.2f}",
            "predicted_return": f"{predicted_return:.2%}"
        }
    }
    return replace_nan_with_none(results)

# --- Background Tasks ---
def run_script_sync(script_name: str, sid: str, loop, sio_server):
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    python_executable = sys.executable
    try:
        process = subprocess.Popen(
            [python_executable, '-u', script_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='gbk', errors='replace'
        )
        def emit_log(log_line):
            asyncio.run_coroutine_threadsafe(
                sio_server.emit('log', {'data': log_line}, to=sid), loop
            )
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if line:
                    emit_log(line)
        process.wait()
        if script_name == 'scanner.py':
            result_path = os.path.join(os.path.dirname(__file__), 'predicted_stocks.json')
            if os.path.exists(result_path):
                with open(result_path, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                asyncio.run_coroutine_threadsafe(
                    sio_server.emit('prediction_result', {'data': results}, to=sid), loop
                )
                try: 
                    os.remove(result_path) 
                except: pass
    except Exception as e:
        error_message = f"执行脚本 {script_name} 时发生严重错误: {e}"
        asyncio.run_coroutine_threadsafe(
            sio_server.emit('log', {'data': error_message}, to=sid), loop
        )
    finally:
        asyncio.run_coroutine_threadsafe(
            sio_server.emit('task_done', {'script': script_name}, to=sid), loop
        )

async def run_script(script_name: str, sid: str):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, functools.partial(run_script_sync, script_name, sid, loop, sio)
    )

async def run_diagnose_task(stock_code: str, sid: str):
    loop = asyncio.get_running_loop()
    def log_callback(message):
        asyncio.run_coroutine_threadsafe(
            sio.emit('log', {'data': message}, to=sid), loop
        )
    log_callback(f"开始诊断股票: {stock_code}...")
    try:
        advice = await loop.run_in_executor(None, diagnose_stock, stock_code)
        log_callback(f"诊断完成。")
        asyncio.run_coroutine_threadsafe(
            sio.emit('diagnosis_result', {'stock_code': stock_code, 'result': advice}, to=sid), loop
        )
    except Exception as e:
        error_message = f"诊断股票 {stock_code} 时发生错误: {e}"
        log_callback(error_message)
        asyncio.run_coroutine_threadsafe(
            sio.emit('diagnosis_result', {'stock_code': stock_code, 'result': error_message, 'error': True}, to=sid), loop
        )
    finally:
        asyncio.run_coroutine_threadsafe(
            sio.emit('task_done', {'task': 'diagnose', 'stock_code': stock_code}, to=sid), loop
        )

# --- Endpoints ---

@app.get("/get_signal_logs")
def get_logs():
    return list(signal_logs)

@app.get("/get_btc_signal")
async def btc_signal_for_ea(symbol: str = 'BTC/USDT', timeframe: str = '5m', trade_amount_usdt: float = 100.0,
                             dry_run: bool = True, max_position_size: float = 0.01, max_notional: float = 1000.0):
    def log_wrapper(msg):
        add_global_log(f"[GET /get_btc_signal] {msg}")
    log_wrapper(f"Request: {symbol}, {timeframe}, {trade_amount_usdt} USDT")
    try:
        result = await binance_service.execute_trade_logic(
            symbol=symbol, timeframe=timeframe, trade_amount_usdt=trade_amount_usdt,
            dry_run=dry_run, max_position_size=max_position_size, max_notional=max_notional,
            add_log_func=log_wrapper
        )
        return result
    except Exception as e:
        import traceback
        log_wrapper(f"Error: {e}")
        log_wrapper(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predict")
async def predict_signal_for_ea(symbol: str):
    def log_wrapper(msg):
        add_global_log(f"[GET /predict] {msg}")
    log_wrapper(f"Request: {symbol}")
    try:
        loop = asyncio.get_running_loop()
        def _work():
            end_date = datetime.datetime.now().strftime("%Y%m%d")
            start_date = (datetime.datetime.now() - datetime.timedelta(days=250)).strftime("%Y%m%d")
            market_data = get_any_stock_data(ticker=symbol, start_date=start_date, end_date=end_date)
            if market_data is None or market_data.empty or len(market_data) < 50:
                 return {"signal": "ERROR", "comment": "Insufficient data"}
            return generate_signal_from_data(symbol, market_data, log_wrapper)
        result = await loop.run_in_executor(None, _work)
        if result["signal"] == "ERROR":
            raise HTTPException(status_code=500, detail=result.get("comment", "Unknown Error"))
        return {"signal": result["signal"]}
    except HTTPException as h: raise h
    except Exception as e:
        log_wrapper(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_signal")
async def get_signal_for_ea(request: Request):
    def log_wrapper(msg):
        add_global_log(f"[POST /get_signal] {msg}")
    if platform.system() != "Windows":
        raise HTTPException(status_code=400, detail="MT5 only on Windows")
    try:
        raw_body = await request.body()
        decoded_body = raw_body.decode('utf-8').split('\x00', 1)[0]
        json_data = json.loads(decoded_body)
        info = TickerInfo(**json_data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid Body: {e}")

    try:
        timeframe_map = {'M1': mt5.TIMEFRAME_M1, 'H1': mt5.TIMEFRAME_H1, 'D1': mt5.TIMEFRAME_D1}
        mt5_timeframe = timeframe_map.get(info.timeframe, mt5.TIMEFRAME_H1)
        rates = mt5.copy_rates_from_pos(info.ticker, mt5_timeframe, 0, 200)
        
        if rates is None or len(rates) < 100:
             raise HTTPException(status_code=404, detail="Insufficient MT5 data")

        rates_df = pd.DataFrame(rates)
        rates_df['date'] = pd.to_datetime(rates_df['time'], unit='s')
        rates_df.set_index('date', inplace=True)
        rates_df.rename(columns={'tick_volume': 'volume'}, inplace=True)

        result = generate_signal_from_data(info.ticker, rates_df, log_wrapper)
        if result["signal"] == "ERROR":
            raise HTTPException(status_code=500, detail=result["comment"])

        signal = result["signal"]
        trade_price = rates_df['close'].iloc[-1]
        trade_quantity = 1.0 

        mt5_positions = trader.get_positions()
        current_pos = mt5_positions.get(info.ticker)
        
        has_long = current_pos and current_pos.get('type') == mt5.POSITION_TYPE_BUY
        has_short = current_pos and current_pos.get('type') == mt5.POSITION_TYPE_SELL
        pos_vol = current_pos.get('quantity', 0.0) if current_pos else 0.0

        if signal == "BUY":
            if has_short:
                trader.place_order(info.ticker, "BUY", trade_price, pos_vol)
                log_wrapper(f"Close Short {info.ticker}")
            elif not has_long:
                trader.place_order(info.ticker, "BUY", trade_price, trade_quantity)
                log_wrapper(f"Open Long {info.ticker}")
            elif has_long:
                 trader.place_order(info.ticker, "BUY", trade_price, trade_quantity)
                 log_wrapper(f"Add Long {info.ticker}")
        elif signal == "SELL":
            if has_long:
                trader.place_order(info.ticker, "SELL", trade_price, pos_vol)
                log_wrapper(f"Close Long {info.ticker}")
            elif not has_short:
                 trader.place_order(info.ticker, "SELL", trade_price, trade_quantity)
                 log_wrapper(f"Open Short {info.ticker}")
            elif has_short:
                 trader.place_order(info.ticker, "SELL", trade_price, trade_quantity)
                 log_wrapper(f"Add Short {info.ticker}")

        return {"ticker": info.ticker, "signal": signal}
    except HTTPException as e: raise e
    except Exception as e:
        import traceback
        log_wrapper(f"Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/train_model")
async def train_model_endpoint(train_request: TrainRequest):
    ticker = train_request.ticker
    try:
        python_executable = sys.executable
        script_path = os.path.join(os.path.dirname(__file__), 'model_trainer.py')
        process_env = os.environ.copy()
        process_env["PYTHONIOENCODING"] = "utf-8"
        process = await asyncio.create_subprocess_exec(
            python_executable, script_path, ticker,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=process_env
        )
        stdout, stderr = await process.communicate()
        stdout_decoded = stdout.decode('utf-8', errors='replace')
        stderr_decoded = stderr.decode('utf-8', errors='replace')
        if process.returncode == 0:
            return {"status": "success", "message": f"Training completed for {ticker}", "logs": stdout_decoded}
        else:
            raise HTTPException(status_code=500, detail=f"Training failed: {stderr_decoded}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_trade_logs")
def get_trade_logs():
    return trader.get_trade_log()

@app.get("/get_account_info")
def get_account_info():
    return trader.get_account_info()

@app.post("/strategy/run")
def run_strategy_endpoint(config: StrategyConfig):
    try:
        results = run_strategy_pipeline(config)
        return {"status": "success", "data": results}
    except HTTPException as e: raise e
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute_trade")
async def execute_trade(payload: Dict[str, Any]):
    # Async enabled execute trade using services
    try:
        audit_id = payload.get('audit_id')
        token = payload.get('token')
        exec_token = os.getenv('EXECUTION_TOKEN')
        
        if not exec_token or token != exec_token:
            raise HTTPException(status_code=403, detail='Invalid execution token')
            
        import audit_db
        rec = audit_db.get_by_audit_id(audit_id)
        if not rec:
             raise HTTPException(status_code=404, detail='Audit record not found')
             
        symbol = rec.get('symbol')
        side = rec.get('side')
        qty = float(rec.get('qty') or 0)
        
        if not symbol or not side or not qty:
            raise HTTPException(status_code=422, detail='Audit record invalid')
            
        # Use binance_service
        try:
            order = None
            if side.upper() == 'BUY':
                order = await binance_service.exchange.create_market_buy_order(symbol, qty)
            elif side.upper() == 'SELL':
                order = await binance_service.exchange.create_market_sell_order(symbol, qty)
            
            # Log success
            write_trade_audit({
                'parent_audit_id': audit_id,
                'symbol': symbol,
                'action': 'execute',
                'order': order,
                'simulated': False
            })
            return {"status": "ok", "order": order}
        except Exception as e:
            write_trade_audit({
                'parent_audit_id': audit_id,
                'action': 'execute_attempt',
                'error': str(e)
            })
            raise HTTPException(status_code=500, detail=str(e))
            
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@sio.event
async def connect(sid, environ):
    await sio.emit('log', {'data': 'Connected'}, to=sid)

@sio.event
async def disconnect(sid):
    pass

@sio.on('execute_task')
async def on_execute_task(sid, data):
    task_name = data.get('task')
    script_map = {
        'download': 'data_downloader.py',
        'train': 'model_trainer.py',
        'predict': 'scanner.py'
    }
    if task_name == 'diagnose':
        stock_code = data.get('stock_code')
        if stock_code:
            asyncio.create_task(run_diagnose_task(stock_code, sid))
    elif script_map.get(task_name):
        script_to_run = script_map.get(task_name)
        asyncio.create_task(run_script(script_to_run, sid))
    else:
        await sio.emit('log', {'data': f"Unknown task '{task_name}'"}, to=sid)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)