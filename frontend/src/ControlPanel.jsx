import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import axios from 'axios'; // 导入 axios
import './ControlPanel.css';

// 后端服务器地址
const SOCKET_SERVER_URL = 'http://localhost:8000';

const ControlPanel = () => {
  const [socket, setSocket] = useState(null);
  const [logs, setLogs] = useState([]);
  const [results, setResults] = useState([]);
  const [isTaskRunning, setIsTaskRunning] = useState(false);
  const [tickerToTrain, setTickerToTrain] = useState(''); // 新增 state 用于存储待训练的 ticker
  const logsEndRef = useRef(null);

  // 自动滚动到日志底部
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // 初始化和管理 Socket.IO 连接
  useEffect(() => {
    const newSocket = io(SOCKET_SERVER_URL, {
      transports: ['websocket'],
    });
    setSocket(newSocket);

    newSocket.on('connect', () => {
      console.log('WebSocket 连接成功! Socket ID:', newSocket.id);
      setLogs(prev => [...prev, '成功连接到后端服务！']);
    });

    newSocket.on('log', (message) => {
      console.log('收到 log 消息:', message.data);
      setLogs(prev => [...prev, message.data]);
    });

    newSocket.on('prediction_result', (message) => {
      console.log('收到 prediction_result 消息:', message.data);
      setResults(message.data);
    });

    newSocket.on('task_done', (message) => {
      console.log('收到 task_done 消息:', message.script);
      setLogs(prev => [...prev, `--- 任务 ${message.script} 完成 ---`]);
      setIsTaskRunning(false);
    });

    return () => {
      newSocket.disconnect();
    };
  }, []);

  // 发送执行预定义任务的请求
  const handleExecuteTask = (taskName) => {
    if (socket && !isTaskRunning) {
      setLogs([`请求执行任务: ${taskName}...`]);
      setResults([]);
      setIsTaskRunning(true);
      socket.emit('execute_task', { task: taskName });
    }
  };

  // 新增：处理为指定 ticker 训练模型的请求
  const handleTrainTicker = async () => {
    if (!tickerToTrain) {
      alert('请输入有效的股票/品种代码！');
      return;
    }
    if (isTaskRunning) {
      alert('已有任务在执行中，请稍后再试。');
      return;
    }

    setIsTaskRunning(true);
    setLogs([`请求为 ${tickerToTrain} 训练模型...`]);
    try {
      const response = await axios.post(`${SOCKET_SERVER_URL}/train_model`, {
        ticker: tickerToTrain,
      });
      
      if (response.data.status === 'success') {
        // 将训练脚本的日志添加到日志窗口
        const trainingLogs = response.data.logs.split('\n');
        setLogs(prev => [...prev, ...trainingLogs, `--- ${tickerToTrain} 模型训练成功 ---`]);
      } else {
        setLogs(prev => [...prev, `错误: ${response.data.message}`]);
      }
    } catch (error) {
      const errorMessage = error.response?.data?.detail || error.message;
      console.error('训练模型时发生错误:', errorMessage);
      setLogs(prev => [...prev, `训练模型时发生严重错误: ${errorMessage}`]);
    } finally {
      setIsTaskRunning(false);
    }
  };

  const tasks = [
    { name: 'download', title: '下载最新数据', description: '运行 data_downloader.py，从网络获取最新的股票日线数据并保存到本地。' },
    { name: 'train', title: '训练全局模型', description: '运行 model_trainer.py，使用所有本地数据训练一个通用的股票预测模型。' },
    { name: 'predict', title: 'AI agent选股', description: '运行 scanner.py，加载模型并对所有股票进行分析，选出预期收益最高的股票。' },
  ];

  return (
    <div className="control-panel">
      <h1>量化交易控制台</h1>
      
      <div className="task-cards">
        {/* 预定义任务 */}
        {tasks.map((task) => (
          <div key={task.name} className="card">
            <h2>{task.title}</h2>
            <p>{task.description}</p>
            <button 
              onClick={() => handleExecuteTask(task.name)}
              disabled={isTaskRunning}
            >
              {isTaskRunning ? '任务执行中...' : '开始执行'}
            </button>
          </div>
        ))}

        {/* 新增：为指定 Ticker 训练模型 */}
        <div className="card">
          <h2>训练指定模型</h2>
          <p>为单个股票或外汇品种（例如: AMD, USDCHF）创建或更新模型。</p>
          <input
            type="text"
            value={tickerToTrain}
            onChange={(e) => setTickerToTrain(e.target.value)}
            placeholder="输入股票/品种代码"
            className="ticker-input"
            disabled={isTaskRunning}
          />
          <button 
            onClick={handleTrainTicker}
            disabled={isTaskRunning || !tickerToTrain}
          >
            {isTaskRunning ? '任务执行中...' : '开始训练'}
          </button>
        </div>
      </div>

      <div className="outputs">
        <div className="log-output">
          <h2>实时日志</h2>
          <pre className="log-box">
            {logs.map((log, index) => (
              <div key={index}>{log}</div>
            ))}
            <div ref={logsEndRef} />
          </pre>
        </div>

        <div className="result-output">
          <h2>选股结果</h2>
          <div className="result-table-container">
            {results.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    <th>代码</th>
                    <th>名称</th>
                    <th>预期收益(%)</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((stock, index) => (
                    <tr key={index}>
                      <td>{stock['代码']}</td>
                      <td>{stock['名称']}</td>
                      <td>{stock['predicted_return(%)']}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>暂无结果。请先执行“智能选股”任务。</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;