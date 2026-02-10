import ccxt.async_support as ccxt
import pandas as pd
import asyncio
from config import config
from services.data_service import write_trade_audit, sanitize_for_json
from services.model_service import generate_signal_from_crypto_data

class BinanceTradingService:
    def __init__(self):
        self.enabled = False
        if not config.BINANCE_API_KEY or not config.BINANCE_SECRET_KEY:
            print("⚠️ Warning: Binance keys missing. Trading service disabled.")
            self.exchange = None
            return

        exchange_config = {
            'apiKey': config.BINANCE_API_KEY,
            'secret': config.BINANCE_SECRET_KEY,
            'options': {
                'defaultType': 'future',
            },
            'timeout': 30000,
            'enableRateLimit': True,
        }

        # Configure Proxy if available
        if config.HTTP_PROXY or config.HTTPS_PROXY:
            exchange_config['proxies'] = {
                'http': config.HTTP_PROXY,
                'https': config.HTTPS_PROXY or config.HTTP_PROXY
            }
            print(f"🌍 Using Proxy: {exchange_config['proxies']}")

        try:
            self.exchange = ccxt.binance(exchange_config)
            if config.BINANCE_TESTNET:
                self.exchange.set_sandbox_mode(True)
            
            # Explicitly set aiohttp_proxy for async ccxt
            if config.HTTP_PROXY:
                self.exchange.aiohttp_proxy = config.HTTP_PROXY
                print(f"🌍 CCXT aiohttp_proxy set to {config.HTTP_PROXY}")
                
            self.enabled = True
        except Exception as e:
            print(f"❌ Failed to initialize ccxt: {e}")
            self.exchange = None
            self.enabled = False

        self.markets_loaded = False

    async def ensure_markets(self):
        if not self.enabled or not self.exchange:
            return False
            
        if not self.markets_loaded:
            try:
                await self.exchange.load_markets()
                self.markets_loaded = True
                print("✅ Binance markets loaded.")
                return True
            except Exception as e:
                print(f"❌ Failed to load markets: {e}")
                # Don't disable entirely, retry might work later? 
                # For now, let's keep enabled but return False so callers know
                return False
        return True

    async def close(self):
        if self.exchange:
            await self.exchange.close()

    async def get_klines(self, symbol: str, timeframe: str = '5m', limit: int = 250) -> pd.DataFrame:
        if not await self.ensure_markets():
             raise Exception("Binance markets not loaded")
             
        # symbol e.g., 'BTC/USDT'
        ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('date', inplace=True)
        return df

    async def get_position(self, symbol: str):
        if not await self.ensure_markets():
            return 0.0, None

        try:
            positions = await self.exchange.fetch_positions([symbol])
            target_pos = None
            for p in positions:
                if p['symbol'] == symbol:
                    target_pos = p
                    break
            
            if target_pos:
                amt = float(target_pos['contracts'])
                raw_amt = float(target_pos['info'].get('positionAmt', 0))
                side = 'long' if raw_amt > 0 else 'short'
                return raw_amt, side
            return 0.0, None
        except Exception as e:
            print(f"Error fetching position: {e}")
            return 0.0, None

    async def execute_trade_logic(self, symbol: str, timeframe: str, trade_amount_usdt: float, 
                           dry_run: bool, max_position_size: float, max_notional: float,
                           add_log_func):
        
        if not self.enabled:
            return {"symbol": symbol, "signal": "ERROR", "comment": "Trading service disabled (keys missing or init failed)"}

        # 1. Fetch Data
        try:
            df = await self.get_klines(symbol, timeframe)
        except Exception as e:
            add_log_func(f"Failed to fetch klines: {e}")
            return {"symbol": symbol, "signal": "ERROR", "comment": f"Fetch klines failed: {e}"}

        # 2. Generate Signal (CPU bound, run in executor)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, 
            generate_signal_from_crypto_data, 
            symbol, df, add_log_func
        )
        
        signal = result.get("signal", "ERROR")
        pred = result.get('prediction', 'N/A')
        comment = f"Model prediction: {pred}"
        
        if signal not in ["BUY", "SELL"]:
            return {"symbol": symbol, "signal": signal, "prediction": pred, "comment": comment}

        # 3. Execution Logic
        pos_amt, pos_side = await self.get_position(symbol)
        add_log_func(f"Current Position: {pos_amt} ({pos_side})")
        
        current_price = df['close'].iloc[-1]
        
        # Calculate Qty
        try:
            raw_qty = trade_amount_usdt / current_price
        except ZeroDivisionError:
             return {"symbol": symbol, "signal": "ERROR", "comment": "Current price is zero"}
        
        # Check Notional Cap
        if trade_amount_usdt > max_notional:
            add_log_func(f"Refused: Notional {trade_amount_usdt} > {max_notional}")
            return self._rejected_audit(symbol, signal, 'max_notional_exceeded', dry_run, comment)

        # Check max position size cap
        if raw_qty > max_position_size:
             raw_qty = max_position_size
             add_log_func(f"Capped qty to {max_position_size}")

        try:
            amount_str = self.exchange.amount_to_precision(symbol, raw_qty)
            adjusted_qty = float(amount_str)
        except Exception as e:
             add_log_func(f"Precision adjustment failed: {e}")
             return self._rejected_audit(symbol, signal, 'precision_error', dry_run, str(e))

        order = None
        audit_id = None
        
        if signal == "BUY":
            # Close Short
            if pos_side == 'short':
                close_qty = abs(pos_amt) 
                add_log_func(f"Closing Short: {close_qty}")
                if not dry_run:
                    try:
                        order = await self.exchange.create_market_buy_order(symbol, close_qty, params={'reduceOnly': True})
                        self._audit_trade(symbol, signal, 'close', 'BUY', close_qty, current_price, dry_run, order)
                    except Exception as e:
                        add_log_func(f"Close Short Failed: {e}")
                else:
                    add_log_func("DRY RUN: Close Short")
            
            # Open Long
            add_log_func(f"Opening Long: {adjusted_qty}")
            if not dry_run:
                try:
                    order = await self.exchange.create_market_buy_order(symbol, adjusted_qty)
                    audit_id = self._audit_trade(symbol, signal, 'open', 'BUY', adjusted_qty, current_price, dry_run, order)
                except Exception as e:
                    add_log_func(f"Open Long Failed: {e}")
            else:
                add_log_func("DRY RUN: Open Long")
                audit_id = self._audit_trade(symbol, signal, 'open', 'BUY', adjusted_qty, current_price, dry_run, {"simulated": True})

        elif signal == "SELL":
            # Close Long
            if pos_side == 'long':
                close_qty = abs(pos_amt)
                add_log_func(f"Closing Long: {close_qty}")
                if not dry_run:
                    try:
                        order = await self.exchange.create_market_sell_order(symbol, close_qty, params={'reduceOnly': True})
                        self._audit_trade(symbol, signal, 'close', 'SELL', close_qty, current_price, dry_run, order)
                    except Exception as e:
                        add_log_func(f"Close Long Failed: {e}")
                else:
                    add_log_func("DRY RUN: Close Long")

            # Open Short
            add_log_func(f"Opening Short: {adjusted_qty}")
            if not dry_run:
                try:
                    order = await self.exchange.create_market_sell_order(symbol, adjusted_qty)
                    audit_id = self._audit_trade(symbol, signal, 'open', 'SELL', adjusted_qty, current_price, dry_run, order)
                except Exception as e:
                    add_log_func(f"Open Short Failed: {e}")
            else:
                 add_log_func("DRY RUN: Open Short")
                 audit_id = self._audit_trade(symbol, signal, 'open', 'SELL', adjusted_qty, current_price, dry_run, {"simulated": True})

        return {"symbol": symbol, "signal": signal, "comment": sanitize_for_json(comment), "audit_id": audit_id, "dry_run": dry_run}

    def _rejected_audit(self, symbol, signal, reason, dry_run, comment):
        rec = {
            'symbol': symbol,
            'signal': signal,
            'action': 'rejected',
            'reason': reason,
            'simulated': dry_run,
            'comment': comment
        }
        aid = write_trade_audit(rec)
        import uuid
        return {"symbol": symbol, "signal": signal, "comment": comment, "audit_id": aid or uuid.uuid4().hex}

    def _audit_trade(self, symbol, signal, action, side, qty, price, dry_run, order):
        rec = {
            'symbol': symbol,
            'signal': signal,
            'action': action,
            'side': side,
            'qty': qty,
            'price': float(price),
            'simulated': dry_run,
            'order': order
        }
        return write_trade_audit(rec)
