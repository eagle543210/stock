import csv
import json
import os
import datetime
import uuid
import numpy as np
import pandas as pd
from config import config

# Try import audit_db, if fails, mock it or handle gracefully as in original code
try:
    import audit_db
except ImportError:
    audit_db = None

def replace_nan_with_none(data):
    if isinstance(data, dict):
        return {k: replace_nan_with_none(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [replace_nan_with_none(i) for i in data]
    elif isinstance(data, (np.floating, float)):
        if np.isnan(data) or np.isinf(data):
            return None
    return data

def sanitize_for_json(text: str) -> str:
    """移除或转义可能导致JSON解析失败的字符"""
    if not isinstance(text, str):
        text = str(text)
    # 移除换行、制表符等控制字符
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return text

def log_base_prediction(ticker: str, prediction: float):
    """将基础模型的预测记录到CSV文件中，使用绝对路径并增加日志。"""
    try:
        header_needed = not os.path.exists(config.PREDICTION_LOG_FILE) or os.path.getsize(config.PREDICTION_LOG_FILE) == 0

        with open(config.PREDICTION_LOG_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if header_needed:
                writer.writerow(['prediction_date', 'ticker', 'base_prediction', 'actual_5d_return', 'error'])
            
            # 写入预测数据
            row_data = [datetime.datetime.now().isoformat(), ticker, prediction, '', '']
            writer.writerow(row_data)

    except Exception as e:
        print(f"!!!!!! 日志记录错误: 写入 '{config.PREDICTION_LOG_FILE}' 失败: {e} !!!!!!")

def write_trade_audit(record: dict) -> str:
    """Append audit record to JSONL file and insert into SQLite; return audit_id."""
    try:
        audit_id = record.get('audit_id') or uuid.uuid4().hex
        record_out = dict(record)
        record_out.setdefault('timestamp', datetime.datetime.now().isoformat())
        record_out['audit_id'] = audit_id

        # write JSONL file
        try:
            with open(config.TRADE_AUDIT_LOG, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(record_out, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"⚠️ write_trade_audit 文件写入失败: {e}")

        # write to sqlite (best-effort)
        if audit_db:
            try:
                audit_db.insert_record(record_out)
            except Exception as e:
                print(f"⚠️ write_trade_audit SQLite 写入失败: {e}")

        return audit_id
    except Exception as e:
        print(f"⚠️ write_trade_audit 失败: {e}")
        return ''
