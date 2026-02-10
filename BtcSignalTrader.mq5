//+------------------------------------------------------------------+
//|                                             BtcSignalTrader.mq5 |
//|                                  Copyright 2025, Gemini Assistant |
//|                                             https://gemini.google.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Gemini Assistant"
#property link      "https://gemini.google.com"
#property version   "1.04" // 版本更新：使用定时器确保持续请求
#property description "从外部Python API获取BTC/USDT交易信号"

//--- EA 输入参数
input string api_url = "http://127.0.0.1:8000/get_btc_signal"; // Python后端BTC信号API地址
input string  trade_symbol = "BTC"; // 要在MT5图表上运行此EA的品种名称 (例如: BTC, BTCUSDT)
input ENUM_TIMEFRAMES chart_timeframe = PERIOD_M5; // EA请求信号的时间周期
input int    signal_check_interval_seconds = 300;             // 信号检查间隔 (秒), 300秒 = 5分钟
input int    dry_run = 1;                                      // 是否模拟运行: 0=实际下单, 1=模拟测试 (默认安全的模拟模式)
input double trade_amount_usdt = 100.0;                        // 单笔交易金额 (USDT)

//--- 全局变量
// datetime last_bar_time;   // 不再需要，由定时器控制

//--- 函数声明
string GetSignalFromAPI();
void ProcessSignal();
string GetJsonValue(string json_string, string key);
string PeriodToString(ENUM_TIMEFRAMES period);
string ConvertMT5SymbolToApiSymbol(string mt5_symbol);

//+------------------------------------------------------------------+
//| EA初始化函数                                                     |
//+------------------------------------------------------------------+
int OnInit()
{
    //--- 检查EA是否加载在正确的交易品种上
    if(_Symbol != trade_symbol)
    {
        string msg = StringFormat("此EA被设计为在 %s 上运行，但当前图表是 %s。请加载到正确的图表。", trade_symbol, _Symbol);
        MessageBox(msg, "错误的交易品种", MB_OK | MB_ICONWARNING);
        return(INIT_FAILED);
    }

    //--- 初始化K线时间
    // last_bar_time = 0; // 不再需要

    Print("BTC信号EA初始化成功！");
    Print("API URL: ", api_url);
    PrintFormat("信号检查间隔: %d 秒", signal_check_interval_seconds);

    // --- 设置定时器 ---
    EventSetTimer(signal_check_interval_seconds);
    
    // 立即执行一次以获取当前信号
    ProcessSignal();

    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| EA反初始化函数                                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // --- 关闭定时器 ---
    EventKillTimer();
    Print("BTC信号EA已移除。");
}

//+------------------------------------------------------------------+
//| EA核心逻辑函数 (每个报价到来时执行)                              |
//+------------------------------------------------------------------+
void OnTick()
{
    // 信号处理由OnTimer负责
}

//+------------------------------------------------------------------+
//| 定时器事件处理函数                                                |
//+------------------------------------------------------------------+
void OnTimer()
{
    Print("定时器触发，准备向API请求信号...");
    ProcessSignal();
}

//+------------------------------------------------------------------+
//| 获取并处理信号的核心函数                                           |
//+------------------------------------------------------------------+
void ProcessSignal()
{
    string response = GetSignalFromAPI();
    
    if(response == "ERROR" || response == "HTTP_ERROR" || response == "PARSE_ERROR")
    {
        Print("获取信号失败，��检查后端服务和MT5日志。");
        return;
    }
    
    // --- 解析JSON响应 ---
    // 简单的JSON解析，提取 "signal" 和 "comment" 的值
    string signal = GetJsonValue(response, "signal");
    string comment = GetJsonValue(response, "comment");
    
    PrintFormat("从API获取到信号: [%s], 备注: %s", signal, comment);
    
    // 在图表左上角显示当前信号
    Comment("当前BTC信号: ", signal, "\n",
            "备注: ", comment, "\n",
            "最后更新: ", TimeToString(TimeCurrent()));
            
    // --- 可以在这里添加通知逻辑 ---
    // if(signal == "BUY" || signal == "SELL")
    // {
    //     SendNotification("新的BTC交易信号: " + signal);
    //     Alert("新的BTC交易信号: ", signal, " | 备注: ", comment);
    // }
}


//+------------------------------------------------------------------+
//| 从Python API获取交易信号                                         |
//+------------------------------------------------------------------+
string GetSignalFromAPI()
{
    uchar result_data[];
    string result_headers;
    uchar empty_data[]; // 定义一个空的uchar数组，用于GET请求的data参数

    // 构建带参数的URL
    string api_symbol = ConvertMT5SymbolToApiSymbol(trade_symbol);
    string timeframe_str = PeriodToString(chart_timeframe);
    string request_url = api_url 
        + "?symbol=" + api_symbol 
        + "&timeframe=" + timeframe_str
        + "&dry_run=" + IntegerToString(dry_run)
        + "&trade_amount_usdt=" + DoubleToString(trade_amount_usdt, 1);

    string request_headers = "Content-Type: application/json\r\n";

    ResetLastError();
    
    Print("准备发送GET请求到: ", request_url);

    int res = WebRequest("GET", request_url, request_headers, 10000, empty_data, result_data, result_headers); // 超时设为10秒

    if(res == -1)
    {
        Print("WebRequest 错误代码: ", GetLastError());
        return "ERROR";
    }
    
    if(res != 200)
    {
        Print("WebRequest 返回HTTP状态码: ", res);
        return "HTTP_ERROR";
    }

    string response_text = CharArrayToString(result_data, 0, WHOLE_ARRAY, CP_UTF8);
    Print("API响应文本: ", response_text);
    
    return response_text;
}

//+------------------------------------------------------------------+
//| 简单的JSON解析函数，用于从响应中提取指定键的值                     |
//+------------------------------------------------------------------+
string GetJsonValue(string json_string, string key)
{
    string search_key = "\"" + key + "\":\"";
    int start_pos = StringFind(json_string, search_key);
    
    if(start_pos == -1)
    {
        return "N/A"; // 未找到键
    }
    
    start_pos += StringLen(search_key);
    int end_pos = StringFind(json_string, "\"", start_pos);
    
    if(end_pos == -1)
    {
        return "N/A"; // 未找到结束引号
    }
    
    return StringSubstr(json_string, start_pos, end_pos - start_pos);
}

//+------------------------------------------------------------------+
//| 将MQL5的ENUM_TIMEFRAMES转换为后端可识别的字符串                    |
//+------------------------------------------------------------------+
string PeriodToString(ENUM_TIMEFRAMES period)
{
    switch(period)
    {
        case PERIOD_M1:  return "1m";
        case PERIOD_M5:  return "5m";
        case PERIOD_M15: return "15m";
        case PERIOD_M30: return "30m";
        case PERIOD_H1:  return "1h";
        case PERIOD_H4:  return "4h";
        case PERIOD_D1:  return "1d";
        case PERIOD_W1:  return "1w";
        case PERIOD_MN1: return "1M";
        default:         return "1h"; // 默认返回1小时
    }
}

//+------------------------------------------------------------------+
//| 将MT5品种名称转换为后端API期望的加密货币交易对格式 (例如 BTCUSDT -> BTC/USDT) |
//+------------------------------------------------------------------+
string ConvertMT5SymbolToApiSymbol(string mt5_symbol)
{
    // 假设MT5品种是 BTCUSDT, ETHUSDT 等，需要转换为 BTC/USDT, ETH/USDT
    if (StringLen(mt5_symbol) > 4 && StringSubstr(mt5_symbol, StringLen(mt5_symbol) - 4) == "USDT")
    {
        return StringSubstr(mt5_symbol, 0, StringLen(mt5_symbol) - 4) + "/USDT";
    }
    // 如果是 BTC，也转换为 BTC/USDT
    if (mt5_symbol == "BTC")
    {
        return "BTC/USDT";
    }
    // 如果是其他格式，例如 BTC，则直接返回
    return mt5_symbol;
}
//+------------------------------------------------------------------+