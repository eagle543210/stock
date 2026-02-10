import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './MT5Trader.css';

const MT5Trader = () => {
    const [ticker, setTicker] = useState('NVDA');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [successMessage, setSuccessMessage] = useState('');
    const [signalLogs, setSignalLogs] = useState([]);

    // --- 模型训练逻辑 ---
    const handleTrainModel = async () => {
        setIsLoading(true);
        setError(null);
        setSuccessMessage('');

        const config = {
            ticker: ticker,
            train_start_date: '20180101',
            train_end_date: '20221231',
            backtest_start_date: '20230101',
            backtest_end_date: '20231231',
            initial_capital: 100000.0,
            future_days: 5,
        };

        try {
            const response = await axios.post('http://localhost:8000/strategy/run', config);
            if (response.data.status === 'success') {
                setSuccessMessage(`为 ${ticker.toUpperCase()} 训练模型成功！模型文件已保存。`);
            } else {
                setError(response.data.message || '发生未知错误');
            }
        } catch (err) {
            console.error('Error training model:', err);
            setError(err.response?.data?.detail || err.message || '运行策略时发生网络错误');
        } finally {
            setIsLoading(false);
        }
    };
    
    // --- 信号日志获取逻辑 ---
    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const response = await axios.get('http://localhost:8000/get_signal_logs');
                setSignalLogs(response.data);
            } catch (error) {
                console.error("Failed to fetch signal logs:", error);
                // 可以在这里设置一个错误状态来显示在UI上
            }
        };

        fetchLogs(); // 立即获取一次
        const interval = setInterval(fetchLogs, 5000); // 每5秒轮询一次

        return () => clearInterval(interval); // 组件卸载时清除定时器
    }, []);


    return (
        <div className="mt5-trader-container">
            <h1>MT5 EA 交易控制台</h1>

            <div className="card">
                <h2>1. 模型训练</h2>
                <p>为指定的交易品种下载最新数据并训练预测模型。模型将被保存在后端，供MT5 EA使用。</p>
                <div className="input-group">
                    <input
                        type="text"
                        value={ticker}
                        onChange={(e) => setTicker(e.target.value)}
                        placeholder="例如: NVDA, EURUSD"
                    />
                    <button onClick={handleTrainModel} disabled={isLoading}>
                        {isLoading ? `正在为 ${ticker.toUpperCase()} 训练...` : `开始训练 ${ticker.toUpperCase()}`}
                    </button>
                </div>
                {successMessage && <div className="success-message">{successMessage}</div>}
                {error && <div className="error-message">错误: {error}</div>}
            </div>

            <div className="card">
                <h2>2. 实时信号日志</h2>
                <p>实时显示 Python API 为 MT5 EA 生成的交易信号。</p>
                <div className="log-box">
                    {signalLogs.length > 0 ? (
                        signalLogs.map((log, index) => <div key={index}>{log}</div>)
                    ) : (
                        <p>等待信号...</p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default MT5Trader;
