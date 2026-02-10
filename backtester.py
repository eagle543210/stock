import pandas as pd
import numpy as np
import joblib
from typing import List, Dict, Any

class Backtester:
    def __init__(self, data: pd.DataFrame, model_path: str, features: List[str], initial_capital: float = 100000.0):
        """
        初始化回���器。
        """
        if data.empty:
            raise ValueError("回测数据不能为空。")
        if not all(f in data.columns for f in features):
            missing_features = [f for f in features if f not in data.columns]
            raise ValueError(f"回测数据缺少以下特征列: {missing_features}")

        self.data = data.copy()
        
        # --- 修复：确保 DataFrame 有一个 DatetimeIndex ---
        # 策略：完全避免使用 pd.to_datetime，因为存在"重复键"问题
        
        # 情况 1: 已经有 DatetimeIndex
        if isinstance(self.data.index, pd.DatetimeIndex):
            # 删除可能存在的 date 列（避免重复）
            if 'date' in self.data.columns:
                self.data = self.data.drop(columns=['date'])
        
        # 情况 2: 没有 DatetimeIndex，但有 date 列
        elif 'date' in self.data.columns:
            print(f"[DEBUG] date 列存在")
            print(f"[DEBUG] date 列的类型: {type(self.data['date'])}")
            
            # 检查 date 是否是 DataFrame（这是问题的根源！）
            if isinstance(self.data['date'], pd.DataFrame):
                print("[DEBUG] ⚠️ date 列是 DataFrame！这是由于 merge 操作导致的")
                print(f"[DEBUG] date DataFrame 的列: {self.data['date'].columns.tolist()}")
                
                # 尝试从 DataFrame 中提取第一列作为日期
                if len(self.data['date'].columns) > 0:
                    first_col = self.data['date'].columns[0]
                    date_col = self.data['date'][first_col].copy()
                    print(f"[DEBUG] 使用 date DataFrame 的第一列: {first_col}")
                else:
                    raise ValueError("date 列是空的 DataFrame")
            else:
                # date 是正常的 Series
                date_col = self.data['date'].copy()
                print(f"[DEBUG] date 列是 Series，dtype: {date_col.dtype}")
            
            print(f"[DEBUG] date 列前3个值: {date_col.head(3).tolist()}")
            print(f"[DEBUG] date 列第一个值的类型: {type(date_col.iloc[0])}")
            
            # 检查是否已经是 datetime 类型
            if pd.api.types.is_datetime64_any_dtype(date_col):
                print("[DEBUG] date 列已经是 datetime64 类型，直接使用")
                # 直接使用 DatetimeIndex 构造函数（不调用 pd.to_datetime）
                new_index = pd.DatetimeIndex(date_col.values)
            else:
                print(f"[DEBUG] date 列不是 datetime 类型，尝试转换")
                # 尝试逐个转换（避免批量转换的"重复键"问题）
                try:
                    # 方法1: 使用 .values 然后构造 DatetimeIndex
                    new_index = pd.DatetimeIndex(date_col.values)
                except:
                    # 方法2: 逐行转换
                    print("[DEBUG] 使用逐行转换方法")
                    converted_dates = []
                    for val in date_col:
                        if isinstance(val, pd.Timestamp):
                            converted_dates.append(val)
                        elif isinstance(val, str):
                            converted_dates.append(pd.Timestamp(val))
                        else:
                            # 尝试转换
                            try:
                                converted_dates.append(pd.Timestamp(val))
                            except:
                                converted_dates.append(pd.NaT)
                    new_index = pd.DatetimeIndex(converted_dates)
            
            # 删除 date 列并设置新索引
            self.data = self.data.drop(columns=['date'])
            self.data.index = new_index
            
            # 删除任何 NaT 行
            self.data = self.data[self.data.index.notna()]
            print(f"[DEBUG] 成功设置 DatetimeIndex，行数: {len(self.data)}")
        
        # 情况 3: 既没有 DatetimeIndex 也没有 date 列
        else:
            print("[DEBUG] 没有 date 列，尝试转换现有 index")
            # 尝试将现有 index 转换为 DatetimeIndex
            try:
                self.data.index = pd.DatetimeIndex(self.data.index.values)
                self.data = self.data[self.data.index.notna()]
            except Exception as e:
                raise ValueError(f"无法创建 DatetimeIndex: {e}")
        
        # --- 修复结束 ---

        self.model = joblib.load(model_path)
        self.features = features
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.shares = 0
        self.average_cost_basis = 0.0 # 追踪平均持仓成本
        self.portfolio_value = []
        self.trades = []
        self.daily_returns = []

        print(f"回测器初始化完成，初始资金: {self.initial_capital}")

    def _calculate_portfolio_value(self, current_price: float) -> float:
        return self.capital + self.shares * current_price

    def run_backtest(self, transaction_cost_rate: float = 0.0003, slippage_rate: float = 0.0001):
        """
        运行回测。
        """
        print("开始运行回测...")
        for i in range(len(self.data)):
            current_date = self.data.index[i]
            current_row = self.data.iloc[i]
            current_price = current_row['close']

            if not all(pd.notna(current_row[f]) for f in self.features):
                signal = 0
            else:
                X_current = pd.DataFrame([current_row[self.features]])
                predicted_return = self.model.predict(X_current)[0]
                
                if predicted_return > 0.01: # Buy signal if predicted return is above threshold
                    signal = 1
                elif predicted_return < -0.01: # Sell signal if predicted return is below threshold
                    signal = -1
                else:
                    signal = 0

            if signal != 0:
                print(f"Date: {current_date.date()}, Signal: {signal}, Price: {current_price}")

            if signal == 1: # Buy
                if self.capital > 0:
                    buy_amount = self.capital * 0.2
                    num_shares_to_buy = int(buy_amount / current_price)
                    if num_shares_to_buy > 0:
                        cost = num_shares_to_buy * current_price
                        transaction_cost = cost * transaction_cost_rate
                        slippage_cost = cost * slippage_rate
                        total_cost = cost + transaction_cost + slippage_cost

                        if self.capital >= total_cost:
                            old_total_value = self.average_cost_basis * self.shares
                            new_total_value = old_total_value + total_cost
                            
                            self.capital -= total_cost
                            self.shares += num_shares_to_buy
                            self.average_cost_basis = new_total_value / self.shares if self.shares > 0 else 0

                            self.trades.append({
                                'date': current_date, 'type': 'BUY', 'price': current_price,
                                'shares': num_shares_to_buy, 'cost': total_cost
                            })
                            print(f"  -> Executed BUY: {num_shares_to_buy} shares @ {current_price:.2f}")

            elif signal == -1: # Sell
                if self.shares > 0:
                    num_shares_to_sell = int(self.shares * 0.5)
                    if num_shares_to_sell > 0:
                        revenue = num_shares_to_sell * current_price
                        transaction_cost = revenue * transaction_cost_rate
                        slippage_cost = revenue * slippage_rate
                        total_revenue = revenue - transaction_cost - slippage_cost

                        cost_of_sold_shares = self.average_cost_basis * num_shares_to_sell
                        profit_loss = total_revenue - cost_of_sold_shares

                        self.capital += total_revenue
                        self.shares -= num_shares_to_sell
                        if self.shares == 0:
                            self.average_cost_basis = 0

                        self.trades.append({
                            'date': current_date, 'type': 'SELL', 'price': current_price,
                            'shares': num_shares_to_sell, 'revenue': total_revenue,
                            'profit_loss': profit_loss
                        })
                        print(f"  -> Executed SELL: {num_shares_to_sell} shares @ {current_price:.2f}, P/L: {profit_loss:.2f}")

            current_portfolio_value = self._calculate_portfolio_value(current_price)
            self.portfolio_value.append(current_portfolio_value)

            if i > 0:
                prev_portfolio_value = self.portfolio_value[i-1]
                daily_ret = (current_portfolio_value - prev_portfolio_value) / prev_portfolio_value if prev_portfolio_value != 0 else 0
                self.daily_returns.append(daily_ret)
            else:
                self.daily_returns.append(0)

        print("回测运行结束。")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        计算并返回回测的性能指标。
        """
        if not self.portfolio_value:
            return {"Error": "回测尚未运行，无法计算性能指标。"}

        final_value = self.portfolio_value[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital

        num_trading_days = len(self.data)
        annualized_return = (1 + total_return)**(252 / num_trading_days) - 1 if num_trading_days > 0 else 0

        daily_returns_series = pd.Series(self.daily_returns)
        sharpe_ratio = daily_returns_series.mean() / daily_returns_series.std() * np.sqrt(252) if len(daily_returns_series) > 1 and daily_returns_series.std() != 0 else 0

        portfolio_series = pd.Series(self.portfolio_value)
        peak = portfolio_series.expanding(min_periods=1).max()
        drawdown = (portfolio_series - peak) / peak
        max_drawdown = drawdown.min() if not drawdown.empty else 0

        sell_trades = [t for t in self.trades if t['type'] == 'SELL']
        print("\n--- Sell Trade Details (for debugging) ---")
        if not sell_trades:
            print("No sell trades were executed.")
        else:
            for t in sell_trades:
                profit_loss_str = f"{t.get('profit_loss', 0):.2f}" if 'profit_loss' in t else "N/A"
                print(f"Date: {t['date'].date()}, Shares: {t['shares']}, Revenue: {t['revenue']:.2f}, P/L: {profit_loss_str}")
        print("------------------------------------------\n")

        wins = sum(1 for trade in sell_trades if trade.get('profit_loss', 0) > 0)
        total_completed_trades = len(sell_trades)
        win_rate = wins / total_completed_trades if total_completed_trades > 0 else 0

        metrics = {
            "Initial Capital": self.initial_capital,
            "Final Capital": self.capital,
            "Final Portfolio Value": final_value,
            "Total Return": f"{total_return:.2%}",
            "Annualized Return": f"{annualized_return:.2%}",
            "Sharpe Ratio": f"{sharpe_ratio:.2f}",
            "Max Drawdown": f"{max_drawdown:.2%}",
            "Number of Trades": len(self.trades),
            "Win Rate": f"{win_rate:.2%}"
        }
        return metrics

if __name__ == '__main__':
    from data_handler import get_stock_data
    from feature_generator import generate_features
    from model_trainer import create_target_labels, train_model
    import os

    ticker_symbol = '600519'
    start_date_train = '20180101'
    end_date_train = '20221231'
    start_date_backtest = '20230101'
    end_date_backtest = '20231231'

    print("--- 准备训练数据 ---")
    raw_data_train = get_stock_data(ticker=ticker_symbol, start_date=start_date_train, end_date=end_date_train)
    if raw_data_train.empty:
        print("无法获取训练数据，退出。")
        exit()
    data_with_features_train = generate_features(raw_data_train.copy())
    data_with_target_train = create_target_labels(data_with_features_train.copy(), future_days=20)

    features_to_use = [
        'SMA_10', 'SMA_20', 'SMA_50',
        'RSI_14',
        'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
        'BBL_20_2.0_2.0', 'BBM_20_2.0_2.0', 'BBU_20_2.0_2.0', 'BBB_20_2.0_2.0', 'BBP_20_2.0_2.0',
        'STOCHk_14_3_3', 'STOCHd_14_3_3',
        'ATRr_14',
        'MOM_10',
        'MFI_14',
        'WILLR_14',
        'OBV'
    ]

    model_save_path = 'M:\\stock\\random_forest_model.joblib'
    train_model(data_with_target_train.copy(), features=features_to_use, target_col='future_20d_return', model_path=model_save_path)

    if not os.path.exists(model_save_path):
        print(f"模型文件 {model_save_path} 不存在，无法进行回测。")
        exit()

    print("\n--- 准备回测数据 ---")
    raw_data_backtest = get_stock_data(ticker=ticker_symbol, start_date=start_date_backtest, end_date=end_date_backtest)
    if raw_data_backtest.empty:
        print("无法获取回测数据，退出。")
        exit()
    data_for_backtest = generate_features(raw_data_backtest.copy())

    if not data_for_backtest.empty:
        backtester = Backtester(data=data_for_backtest, model_path=model_save_path, features=features_to_use, initial_capital=100000.0)
        backtester.run_backtest()
        metrics = backtester.get_performance_metrics()
        print("\n--- 回测性能指标 ---")
        for key, value in metrics.items():
            print(f"{key}: {value}")

