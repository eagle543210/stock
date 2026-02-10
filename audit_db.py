import sqlite3
import threading
import json
import os
from typing import Optional, List, Dict, Any

_lock = threading.Lock()
DB_PATH = os.path.join(os.path.dirname(__file__), 'trade_audit.db')


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock:
        conn = _get_conn()
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id TEXT UNIQUE,
            timestamp TEXT,
            symbol TEXT,
            signal TEXT,
            action TEXT,
            side TEXT,
            qty REAL,
            price REAL,
            simulated INTEGER,
            comment TEXT,
            order_json TEXT,
            raw_json TEXT
        )
        ''')
        conn.commit()
        conn.close()


def insert_record(record: Dict[str, Any]) -> Optional[str]:
    """Insert a record dict (will be serialized) and return audit_id."""
    try:
        init_db()
        audit_id = record.get('audit_id')
        timestamp = record.get('timestamp')
        symbol = record.get('symbol')
        signal = record.get('signal')
        action = record.get('action')
        side = record.get('side')
        qty = record.get('qty')
        price = record.get('price')
        simulated = 1 if record.get('simulated') else 0
        comment = record.get('comment')
        order = record.get('order')
        order_json = json.dumps(order, ensure_ascii=False) if order is not None else None
        raw_json = json.dumps(record, ensure_ascii=False)

        with _lock:
            conn = _get_conn()
            c = conn.cursor()
            c.execute(
                'INSERT OR IGNORE INTO audits (audit_id, timestamp, symbol, signal, action, side, qty, price, simulated, comment, order_json, raw_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                (audit_id, timestamp, symbol, signal, action, side, qty, price, simulated, comment, order_json, raw_json)
            )
            conn.commit()
            conn.close()
        return audit_id
    except Exception:
        return None


def get_by_audit_id(audit_id: str) -> Optional[Dict[str, Any]]:
    init_db()
    conn = _get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM audits WHERE audit_id=? LIMIT 1', (audit_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    out = dict(row)
    # parse order_json / raw_json
    try:
        out['order'] = json.loads(out.get('order_json')) if out.get('order_json') else None
    except Exception:
        out['order'] = None
    try:
        out['raw'] = json.loads(out.get('raw_json')) if out.get('raw_json') else None
    except Exception:
        out['raw'] = None
    return out


def get_recent(limit: int = 50) -> List[Dict[str, Any]]:
    init_db()
    conn = _get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM audits ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    out = []
    for row in rows:
        r = dict(row)
        try:
            r['order'] = json.loads(r.get('order_json')) if r.get('order_json') else None
        except Exception:
            r['order'] = None
        out.append(r)
    return out
