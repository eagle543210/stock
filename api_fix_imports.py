"""
临时修复文件 - 将这个文件的内容复制到 api.py 的开头
"""

import os
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any
import socketio
import asyncio
import subprocess
import json
import functools
import joblib
import sys
import platform
import numpy as np
from collections import deque
import datetime

# MT5 仅在 Windows 上可用 - 条件导入
mt5 = None
if platform.system() == "Windows":
    try:
        import MetaTrader5
        mt5 = MetaTrader5
    except ImportError:
        print("⚠️  MetaTrader5 模块未安装，MT5 功能将不可用")
        mt5 = None
