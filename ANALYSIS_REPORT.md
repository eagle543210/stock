# 股票系统架构分析报告

## 1. 架构概览

该系统采用了 **混合架构**，结合了传统的桌面交易终端 (MT5) 和现代的 Python 微服务 (FastAPI)。

*   **前端/执行端**:
    *   **股票 (A股/美股)**: 使用 MetaTrader 5 (MT5) 作为客户端和执行引擎。
    *   **加密货币**: 使用 MT5 作为信号触发器和可视化界面，但实际下单逻辑在 Python 后端直接连接币安 (Binance)。
*   **后端**: Python FastAPI (`api.py`)，负责信号生成、模型推理、数据处理以及加密货币的订单路由。
*   **数据/模型**: 本地文件系统 (`xxx_model.joblib`, CSV 缓存) 和 SQLite 数据库 (审计日志)。

## 2. 架构合理性分析

### ✅ 优点 (Strengths)

1.  **利用 Python 生态**: 将通过 Python 处理复杂的机器学习推理 (LightGBM/RandomForest)，利用了 Python 丰富的数据科学库，这是 MQL5 难以做到的。
2.  **解耦的信号生成**: 信号逻辑在服务端运行，这意味着可以在不重启客户端 (MT5) 的情况下热更新模型和策略逻辑。
3.  **双重安全机制**: 系统设计了 `dry_run` (模拟) 模式和审计日志 (`trade_audit.db`)，这对于即时交易系统至关重要。
4.  **容错设计**: 代码中对 `pandas_ta` 和 `MetaTrader5` 等依赖做了可选导入处理，增强了系统的移植性（如在非 Windows 环境运行 crypto 部分）。

### ⚠️ 架构风险与不足 (Weaknesses)

1.  **"上帝对象" (God Object) - `api.py`**:
    *   `api.py` 承担了过多的指责：路由处理、业务逻辑、模型加载、数据预处理、甚至交易所 API 交互。
    *   **后果**: 代码难以维护，测试困难，任何小的修改都可能影响整个服务。

2.  **不一致的抽象 (Inconsistent Abstractions)**:
    *   **股票流程**: Python 计算 -> 返回信号 -> **MT5 下单**。
    *   **Crypto 流程**: Python 计算 -> Python 下单 (Binance API) -> 返回结果 -> **MT5 仅显示**。
    *   **后果**: 系统维护者需要维护两套完全不同的执行路径，增加了认知负担。

3.  **并发与性能瓶颈**:
    *   FastAPI 是异步框架 (ASGI)，但核心业务逻辑 (加载模型、pandas 数据处理、同步 HTTP 请求) 是**同步阻塞**的。
    *   **后果**: 当进行繁重的模型推理或数据下载时，整个 API 服务可能会卡顿，导致 MT5 客户端请求超时。

4.  **重复造轮子**:
    *   项目同时引入了 `ccxt` 库和自定义的 `binance_http_client.py`。
    *   `binance_http_client.py` 手动实现了签名和请求逻辑，虽然增加了控制力，但增加了维护成本且不如 `ccxt` 健壮。

## 3. 具体代码问题

### 安全性 (Security)
*   **API Key 管理**: 虽然使用了 `.env`，但代码中有硬编码的路径和潜在的密钥泄露风险（如日志中打印过多详情）。
*   **输入验证**: `get_btc_signal` 端点接收大量参数，但缺乏严格的 Pydantic 模型验证（如 `TickerInfo` 未被该端点使用）。

### 可维护性 (Maintainability)
*   **硬编码**: 
    *   模型路径: `./{model_ticker}_model.joblib` (相对路径依赖于运行目录)。
    *   默认参数: 策略配置分散在各个函数默认参数中。
*   **全局状态**: 大量使用全局变量 (`signal_logs`, `trader`, `sio`)，导致状态管理混乱，且非线程安全。

### 可靠性 (Reliability)
*   **Error Handling**: 虽然有 try-except，但部分异常处理过于宽泛 (catch Exception)，可能掩盖真正的逻辑错误。
*   **数据依赖**: 实时交易依赖于 `data_downloader.py` 的实时下载，如果数据源 (Yahoo/Akshare) 响应慢或反爬，会导致交易失败。

## 4. 改进建议 (Action Plan)

### 短期优化 (Quick Wins)
1.  **统一交易所接口**: 使用 `ccxt` 替换 `binance_http_client.py`，减少自维护代码。
2.  **拆分 `api.py`**: 将业务逻辑移动到 `services/` 目录，路由逻辑保留在 `api.py`。
3.  **异步化**: 将模型推理和网络请求放入 `await run_in_executor` 或使用异步库，避免阻塞主线程。

### 长期重构 (Architecture Refactoring)
1.  **执行层统一**: 建立统一的 `OrderExecution` 抽象层，无论是通过 MT5 还是 Binance API 下单，对上层策略应该是透明的。
2.  **配置中心**: 使用统一的 `config.py` 或 YAML 管理所有策略参数和系统路径。
3.  **数据库升级**: 随着数据量增加，考虑将 SQLite 迁移到 PostgreSQL/TimescaleDB 以支持更复杂的时序查询。
