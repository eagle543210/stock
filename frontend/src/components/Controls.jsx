import React, { useState } from 'react';
import './Controls.css';

// 预设股票列表，用于建议
const stockOptions = [
  { ticker: '600519', name: '贵州茅台' },
  { ticker: '300750', name: '宁德时代' },
  { ticker: '002594', name: '比亚迪' },
  { ticker: '601899', name: '紫金矿业' },
  { ticker: '601318', name: '中国平安' },
];

function Controls({ onRunStrategy }) {
  const [ticker, setTicker] = useState('600519'); // 状态只保存ticker
  const [trainStartDate, setTrainStartDate] = useState('20180101');
  const [trainEndDate, setTrainEndDate] = useState('20221231');
  const [backtestStartDate, setBacktestStartDate] = useState('20230101');
  const [backtestEndDate, setBacktestEndDate] = useState('20231231');
  const [initialCapital, setInitialCapital] = useState(100000.0);
  const [futureDays, setFutureDays] = useState(5);
  const [externalEvent, setExternalEvent] = useState(0);
  const [fundamentalFactors, setFundamentalFactors] = useState([]);

  const handleFactorChange = (e) => {
    const { value, checked } = e.target;
    if (checked) {
      setFundamentalFactors(prev => [...prev, value]);
    } else {
      setFundamentalFactors(prev => prev.filter(factor => factor !== value));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    let formattedTicker = ticker.trim();
    // 如果是纯数字的A股代码，自动添加 'sh.' 前缀 (假设默认是上海交易所)
    // 用户也可以手动输入 'sz.XXXXXX'
    if (/^\d{6}$/.test(formattedTicker) && !formattedTicker.includes('.')) {
      formattedTicker = `sh.${formattedTicker}`;
    }

    // 根据当前ticker查找股票名称
    const stock = stockOptions.find(s => s.ticker === formattedTicker); // 使用格式化后的ticker查找
    const stockName = stock ? stock.name : ''; // 如果找不到，名称为空

    const config = {
      ticker: formattedTicker, // 使用格式化后的ticker
      train_start_date: trainStartDate,
      train_end_date: trainEndDate,
      backtest_start_date: backtestStartDate,
      backtest_end_date: backtestEndDate,
      initial_capital: parseFloat(initialCapital),
      future_days: parseInt(futureDays),
      external_event: parseInt(externalEvent),
      fundamental_factors: fundamentalFactors,
    };
    onRunStrategy(config, stockName); // 传递config和name
  };

  return (
    <div className="controls-panel">
      <h2>策略配置</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>股票代码 (Ticker):</label>
          <input 
            type="text" 
            value={ticker} 
            onChange={(e) => setTicker(e.target.value)} 
            required 
            list="stock-suggestions"
          />
          <datalist id="stock-suggestions">
            {stockOptions.map(stock => (
              <option key={stock.ticker} value={stock.ticker}>
                {stock.name}
              </option>
            ))}
          </datalist>
        </div>
        <div className="form-group">
          <label>训练开始日期 (YYYYMMDD):</label>
          <input type="text" value={trainStartDate} onChange={(e) => setTrainStartDate(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>训练结束日期 (YYYYMMDD):</label>
          <input type="text" value={trainEndDate} onChange={(e) => setTrainEndDate(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>回测开始日期 (YYYYMMDD):</label>
          <input type="text" value={backtestStartDate} onChange={(e) => setBacktestStartDate(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>回测结束日期 (YYYYMMDD):</label>
          <input type="text" value={backtestEndDate} onChange={(e) => setBacktestEndDate(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>初始资金 (Initial Capital):</label>
          <input type="number" value={initialCapital} onChange={(e) => setInitialCapital(e.target.value)} required />
        </div>
        <div className="form-group">
          <label>预测天数 (Future Days):</label>
          <input type="number" value={futureDays} onChange={(e) => setFutureDays(e.target.value)} required min="1" />
        </div>
        <div className="form-group">
          <label>外部事件 (External Event):</label>
          <div className="radio-group">
            <label><input type="radio" name="externalEvent" value="0" checked={externalEvent == 0} onChange={(e) => setExternalEvent(parseInt(e.target.value))} /> 无</label>
            <label><input type="radio" name="externalEvent" value="1" checked={externalEvent == 1} onChange={(e) => setExternalEvent(parseInt(e.target.value))} /> 利好消息</label>
            <label><input type="radio" name="externalEvent" value="-1" checked={externalEvent == -1} onChange={(e) => setExternalEvent(parseInt(e.target.value))} /> 利空消息</label>
          </div>
        </div>

        {/* 基本面因子选择框 */}
        <div className="form-group">
          <label>基本面因子:</label>
          <div className="checkbox-group">
            <label>
              <input type="checkbox" value="pe_ttm" onChange={handleFactorChange} />
              市盈率 (PE)
            </label>
            <label>
              <input type="checkbox" value="pb" onChange={handleFactorChange} />
              市净率 (PB)
            </label>
            <label>
              <input type="checkbox" value="dividend_yield_ttm" onChange={handleFactorChange} />
              股息率
            </label>
          </div>
        </div>

        <button type="submit">运行策略</button>
      </form>
    </div>
  );
}

export default Controls;
