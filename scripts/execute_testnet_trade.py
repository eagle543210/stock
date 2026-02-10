#!/usr/bin/env python3
"""在币安期货测试网上执行一笔小额市价单并立即平仓（用于测试）

注意：脚本会使用仓库根目录下的 .env（如果存在）中的 BINANCE_API_KEY / BINANCE_SECRET_KEY。
只有在你确认要在测试网下单时运行此脚本。
"""

import os
import time
from binance_http_client import BinanceFuturesHTTP


def masked(s: str) -> str:
    if not s:
        return '<missing>'
    return s[:4] + '...' + s[-4:]


def main():
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET_KEY')

    if not api_key or not api_secret:
        print('❌ 未检测到 BINANCE_API_KEY / BINANCE_SECRET_KEY（检查 .env 或环境变量）')
        return 1

    print('使用的 API Key: ', masked(api_key))
    client = BinanceFuturesHTTP(api_key, api_secret, testnet=True)

    symbol = 'BTCUSDT'
    notional = 100.0
    print(f'准备在测试网下单: {symbol}, 面值 {notional} USDT')

    try:
        info = client.get_symbol_info(symbol)
        print('已获取交易规则')
        # 输出关键规则（不打印任何密钥）
        filters = {f['filterType']: f for f in info.get('filters', [])}
        lot = filters.get('LOT_SIZE', {})
        min_qty = lot.get('minQty')
        step = lot.get('stepSize')
        mn = filters.get('MIN_NOTIONAL', {}).get('minNotional') or filters.get('MIN_NOTIONAL', {}).get('notional')
        print(f'  minQty={min_qty}, stepSize={step}, minNotional={mn}')

        # 获取当前价格
        ticker = client.fetch_ticker(symbol)
        price = float(ticker.get('lastPrice') or ticker.get('price') or 0)
        print(f'当前价格: {price}')

        qty = client.adjust_quantity_for_notional(symbol, notional, price=price)
        print(f'调整数量: {qty} (将用于开仓)')

        if qty <= 0:
            print('❌ 计算出的下单数量不合法，已退出')
            return 1

        # 执行开仓 (买入) 并随后平仓
        print('执行测试市价单 (BUY) ...')
        order_buy = client.create_market_order(symbol, 'BUY', qty)
        print('下单返回:', order_buy)

        # 等待短暂时间让交易在模拟环境中执行
        time.sleep(1.5)

        print('立即发送反向市价单 (SELL) 平仓 ...')
        order_sell = client.create_market_order(symbol, 'SELL', qty)
        print('平仓返回:', order_sell)

        print('\n✅ 测试下单流程执行完毕（测试网）。请在币安测试网 UI 中核实订单。')
        return 0

    except Exception as e:
        print('❌ 执行测试下单时发生错误:', e)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
