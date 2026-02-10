import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Routes, Route, Link, Outlet, BrowserRouter, useNavigate } from 'react-router-dom';
import io from 'socket.io-client'; // 导入 socket.io-client
import Controls from './components/Controls';
import KlineChart from './components/KlineChart';
import MetricsDisplay from './components/MetricsDisplay';
import PredictionDisplay from './components/PredictionDisplay';
import FeatureImportanceChart from './components/FeatureImportanceChart';
import ControlPanel from './ControlPanel'; // 导入新的 ControlPanel 组件
import Login from './components/Login'; // 导入 Login 组件
import ProtectedRoute from './components/ProtectedRoute'; // 导入 ProtectedRoute 组件
import MT5Trader from './components/MT5Trader'; // 导入 MT5Trader 组件
import './App.css'; // 确保 App.css 存在或创建它

function Layout({ onLogout }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('isAuthenticated');
    onLogout(false);
    navigate('/login');
  };

  return (
    <div className="layout">
      <nav className="navbar">
        <div>
          <Link to="/">量化回测</Link>
          <Link to="/tasks">量化交易模型训练</Link>
          <Link to="/mt5">MT5 EA交易</Link> {/* 新增导航链接 */}
          <Link to="/diagnose">AI agent诊股</Link> {/* 新增导航链接 */}
        </div>
        <button onClick={handleLogout} className="logout-button">退出登录</button>
      </nav>
      <div className="content">
        <Outlet /> {/* 路由内容将在这里渲染 */}
      </div>
    </div>
  );
}

function BacktestPlatform() {
  const [currentTicker, setCurrentTicker] = useState('');
  const [currentStockName, setCurrentStockName] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleRunStrategy = async (config, stockName) => {
    setLoading(true);
    setError(null);
    setResults(null);
    setCurrentTicker(config.ticker);
    setCurrentStockName(stockName);
    try {
      const response = await axios.post('http://localhost:8000/strategy/run', config);
      if (response.data.status === 'success') {
        setResults(response.data.data);
      } else {
        setError(response.data.message || '未知错误');
      }
    } catch (err) {
      console.error('Error running strategy:', err);
      setError(err.response?.data?.detail || err.message || '运行策略时发生网络错误');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App backtest-container">
      <h1>量化交易智能体回测平台</h1>
      <Controls onRunStrategy={handleRunStrategy} />
      {loading && <div className="loading">正在构建股票代码 {currentTicker}，股票名称：{currentStockName} 的量化模型....</div>}
      {error && <div className="error">错误: {error}</div>}
      <div className="results-container">
        {results && (
          <>
            <PredictionDisplay prediction={results.next_day_prediction} />
            <MetricsDisplay metrics={results.metrics} />
            <FeatureImportanceChart featureImportance={results.feature_importance} />
          </>
        )}
        <KlineChart
          klineData={results?.kline_data}
          buySignals={results?.buy_signals}
          sellSignals={results?.sell_signals}
          isLoading={loading}
          error={error}
        />
      </div>
    </div>
  );
}

function StockDiagnoser() {
    const [stockCode, setStockCode] = useState('');
    const [diagnosisResult, setDiagnosisResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [logs, setLogs] = useState([]);
    const socketRef = useRef(null);
    const logWindowRef = useRef(null);

    useEffect(() => {
        // 连接到 Socket.IO 服务器
        socketRef.current = io('http://localhost:8000');

        socketRef.current.on('connect', () => {
            console.log('Connected to Socket.IO server for diagnosis.');
            setLogs((prevLogs) => [...prevLogs, '成功连接到后端服务！']);
        });

        socketRef.current.on('log', (data) => {
            setLogs((prevLogs) => [...prevLogs, data.data]);
        });

        socketRef.current.on('diagnosis_result', (data) => {
            setDiagnosisResult(data.result);
            setLoading(false);
            if (data.error) {
                setError(data.result);
            }
        });

        socketRef.current.on('task_done', (data) => {
            if (data.task === 'diagnose' && data.stock_code === stockCode) {
                setLoading(false);
                setLogs((prevLogs) => [...prevLogs, `诊断任务完成。`]);
            }
        });

        socketRef.current.on('disconnect', () => {
            console.log('Disconnected from Socket.IO server for diagnosis.');
            setLogs((prevLogs) => [...prevLogs, '与后端服务断开连接。']);
        });

        return () => {
            if (socketRef.current) {
                socketRef.current.disconnect();
            }
        };
    }, [stockCode]); // 依赖 stockCode 以便在股票代码变化时重新连接或更新监听

    useEffect(() => {
        // 滚动到日志窗口底部
        if (logWindowRef.current) {
            logWindowRef.current.scrollTop = logWindowRef.current.scrollHeight;
        }
    }, [logs]);

    const handleDiagnose = () => {
        setLoading(true);
        setError(null);
        setDiagnosisResult(null);
        // setLogs([]); // 不再清除之前的日志

        if (socketRef.current && socketRef.current.connected) {
            socketRef.current.emit('execute_task', { task: 'diagnose', stock_code: stockCode, sid: socketRef.current.id });
            setLogs((prevLogs) => [...prevLogs, `正在为股票 ${stockCode} 启动诊断任务...`]);
        } else {
            setError('Socket.IO 未连接，无法启动诊断任务。');
            setLoading(false);
        }
    };

    return (
        <div className="stock-diagnoser-container">
            <h1>AI agent诊股</h1>
            <div className="input-group">
                <input
                    type="text"
                    value={stockCode}
                    onChange={(e) => setStockCode(e.target.value)}
                    placeholder="输入股票代码 (例如: 600519)"
                    className="stock-input"
                />
                <button onClick={handleDiagnose} disabled={loading} className="diagnose-button">
                    {loading ? '诊断中...' : '开始诊断'}
                </button>
            </div>

            {error && <p className="error-message">错误: {error}</p>}

            {loading && (
                <div className="log-window" ref={logWindowRef}>
                    {logs.map((log, index) => (
                        <p key={index} className="log-entry">{log}</p>
                    ))}
                </div>
            )}

            {diagnosisResult && (
                <div className="diagnosis-result">
                    <h2>诊断结果:</h2>
                    <p>{diagnosisResult}</p>
                </div>
            )}
        </div>
    );
}


function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(
    localStorage.getItem('isAuthenticated') === 'true'
  );

  return (
    <Routes>
      <Route path="/login" element={<Login onLogin={setIsAuthenticated} />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Routes>
              <Route path="/" element={<Layout onLogout={setIsAuthenticated} />}>
                <Route index element={<div className="backtest-container"><BacktestPlatform /></div>} />
                <Route path="tasks" element={<ControlPanel />} />
                <Route path="mt5" element={<MT5Trader />} />
                <Route path="diagnose" element={<StockDiagnoser />} />
              </Route>
            </Routes>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;