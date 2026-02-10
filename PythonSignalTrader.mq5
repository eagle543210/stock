//+------------------------------------------------------------------+
//|                                           PythonSignalTrader.mq5 |
//|                             Copyright 2025, Gemini & Your Name/Company |
//|                                           https://your.url |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Gemini & Your Name/Company"
#property link      "https://your.url"
#property version   "5.09" // 版本更新：使用定时器确保持续请求

// 引入标准库
#include <Trade\Trade.mqh>

//--- EA 输入参数
input string api_url      = "http://127.0.0.1:8000/get_signal"; // Python API服务器的URL
input ulong  magic_number = 6688;                             // EA的魔术号
input double lot_size     = 1;                                // 交易手数
input ulong  slippage     = 10;                               // 允许的滑点 (点)
input int    stop_loss    = 500;                              // 止损 (点)
input int    take_profit  = 1000;                             // 止盈 (点)
input int    signal_check_interval_seconds = 300;             // 信号检查间隔 (秒), 300秒 = 5分钟

//--- 全局变量
CTrade trade;
// datetime last_bar_time; // 不再需要，由定时器控制

//--- 函数声明
string GetSignalFromAPI();
void ProcessSignal();
void OpenPosition(ENUM_POSITION_TYPE type);
void ClosePositions(ENUM_POSITION_TYPE type);
string GetTimeframeString(ENUM_TIMEFRAMES period);

//+------------------------------------------------------------------+
//| EA初始化函数                                                      |
//+------------------------------------------------------------------+
int OnInit()
{
    trade.SetExpertMagicNumber(magic_number);
    trade.SetDeviationInPoints(slippage);
    trade.SetTypeFillingBySymbol(_Symbol);

    Print("PythonSignalTrader EA v5.09 初始化成功 (立即执行一次)");
    Print("API URL: ", api_url);
    PrintFormat("信号检查间隔: %d 秒", signal_check_interval_seconds);

    // --- 设置定时器 ---
    EventSetTimer(signal_check_interval_seconds);

    ProcessSignal(); // 立即执行一次

    // last_bar_time = (datetime)SeriesInfoInteger(_Symbol, _Period, SERIES_LASTBAR_DATE); // 不再需要

    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| EA反初始化函数                                                    |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // --- 关闭定时器 ---
    EventKillTimer();
    Print("PythonSignalTrader EA 已停止，原因代码: ", reason);
}

//+------------------------------------------------------------------+
//| EA Tick处理函数 (现在只用于确保EA活跃，不再直接触发信号处理)        |
//+------------------------------------------------------------------+
void OnTick()
{
    // datetime current_bar_time = (datetime)SeriesInfoInteger(_Symbol, _Period, SERIES_LASTBAR_DATE);
    // 
    // if(current_bar_time > last_bar_time)
    // {
    //     last_bar_time = current_bar_time;
    //     ProcessSignal();
    // }
    // 可以在这里添加一些轻量级的逻辑，但信号处理由OnTimer负责
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
    string signal = GetSignalFromAPI();
    Print("从API获取到信号: ", signal);

    if(signal == "BUY")
    {
        ClosePositions(POSITION_TYPE_SELL);
        OpenPosition(POSITION_TYPE_BUY);
    }
    else if(signal == "SELL")
    {
        ClosePositions(POSITION_TYPE_BUY);
        OpenPosition(POSITION_TYPE_SELL);
    }
    else if(signal == "CLOSE")
    {
        ClosePositions(POSITION_TYPE_BUY);
        ClosePositions(POSITION_TYPE_SELL);
    }
}

//+------------------------------------------------------------------+
//| 时间周期枚举值到字符串的映射函数                                    |
//+------------------------------------------------------------------+
string GetTimeframeString(ENUM_TIMEFRAMES period)
{
    switch(period)
    {
        case PERIOD_M1:  return "M1";
        case PERIOD_M5:  return "M5";
        case PERIOD_M15: return "M15";
        case PERIOD_M30: return "M30";
        case PERIOD_H1:  return "H1";
        case PERIOD_H4:  return "H4";
        case PERIOD_D1:  return "D1";
        case PERIOD_W1:  return "W1";
        case PERIOD_MN1: return "MN1";
        default:         return "H1"; 
    }
}

//+------------------------------------------------------------------+
//| 从Python API获取交易信号 (手动字符串解析)                          |
//+------------------------------------------------------------------+
string GetSignalFromAPI()
{
    string signal = "HOLD"; 
    string symbol_name = _Symbol; 
    string timeframe_str = GetTimeframeString(_Period);

    string json_body = "{\"ticker\":\"" + symbol_name + "\",\"timeframe\":\"" + timeframe_str + "\"}"; 
    uchar post_data[]; 
    StringToCharArray(json_body, post_data, 0, WHOLE_ARRAY, CP_UTF8); 

    string request_headers = "Content-Type: application/json\r\n";
    uchar result_data[]; 
    string result_headers;

    ResetLastError();
    
    Print("准备发送 WebRequest 到: ", api_url);
    Print("请求体: ", json_body);
    
    int res = WebRequest("POST", api_url, request_headers, "", 15000, post_data, ArraySize(post_data), result_data, result_headers);

    if(res == -1)
    {
        Print("WebRequest 错误代码: ", GetLastError());
        return "ERROR";
    }
    
    if(res != 200)
    {
        Print("WebRequest 返回HTTP状态码: ", res);
        string response_text = CharArrayToString(result_data, 0, WHOLE_ARRAY, CP_UTF8);
        Print("API 错误响应: ", response_text); // 打印错误详情
        return "HOLD";
    }

    string response_text = CharArrayToString(result_data, 0, WHOLE_ARRAY, CP_UTF8); 
    Print("API响应文本: ", response_text);
    
    string key = "\"signal\":\"";
    int key_pos = StringFind(response_text, key);

    if(key_pos != -1)
    {
        int start_pos = key_pos + StringLen(key);
        int end_pos = StringFind(response_text, "\"", start_pos); 
        
        if(end_pos != -1)
        {
            signal = StringSubstr(response_text, start_pos, end_pos - start_pos);
        }
        else
        {
            Print("解析错误: 找不到信号值的结束引号。 ", response_text);
        }
    }
    else
    {
        Print("解析错误: 找不到 'signal' 键。 ", response_text);
    }
    
    return signal;
}

//+------------------------------------------------------------------+
//| 开仓函数                                                          |
//+------------------------------------------------------------------+
void OpenPosition(ENUM_POSITION_TYPE type)
{
    if(PositionSelect(_Symbol))
    {
        if(PositionGetInteger(POSITION_TYPE) == type)
        {
            Print("已存在同向仓位，本次不开仓。");
            return;
        }
    }

    double price = 0;
    double sl = 0;
    double tp = 0;
    ENUM_ORDER_TYPE order_type;
    double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

    if(type == POSITION_TYPE_BUY)
    {
        price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
        sl = price - stop_loss * point;
        tp = price + take_profit * point;
        order_type = ORDER_TYPE_BUY;
    }
    else if(type == POSITION_TYPE_SELL)
    {
        price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
        sl = price + stop_loss * point;
        tp = price - take_profit * point;
        order_type = ORDER_TYPE_SELL;
    }
    else
    {
        return;
    }
    
    if(stop_loss <= 0) sl = 0;
    if(take_profit <= 0) tp = 0;

    string format = "准备开仓: %s %s手, 价格: %.*f, SL: %.*f, TP: %.*f";
    string log_msg = StringFormat(format, 
                                  EnumToString(order_type), 
                                  DoubleToString(lot_size, 2), 
                                  _Digits, price, 
                                  _Digits, sl, 
                                  _Digits, tp);
    Print(log_msg);
    
    NormalizeDouble(sl, _Digits);
    NormalizeDouble(tp, _Digits);
    
    trade.PositionOpen(_Symbol, order_type, lot_size, price, sl, tp);
} 

//+------------------------------------------------------------------+
//| 平仓函数                                                          |
//+------------------------------------------------------------------+
void ClosePositions(ENUM_POSITION_TYPE type)
{
    ulong ticket = 0; 
    
    for(int i = PositionsTotal() - 1; i >= 0; i--) 
    {
        if(PositionSelect(PositionGetTicket(i))) 
        { 
            if(PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == magic_number)
            {
                if(PositionGetInteger(POSITION_TYPE) == type)
                {
                    ticket = PositionGetInteger(POSITION_TICKET);
                    string format = "准备平仓: %s Ticket #%lu";
                    string log_msg = StringFormat(format, EnumToString(type), ticket); 
                    
                    Print(log_msg); 
                    
                    trade.PositionClose(ticket, slippage);
                }
            }
        }
    }
}
//+------------------------------------------------------------------+
