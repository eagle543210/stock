import os
import joblib
import pandas as pd
import lightgbm as lgb
from sklearn.ensemble import RandomForestRegressor
from config import config
from services.data_service import log_base_prediction

# Assuming these modules are available in the path
try:
    from feature_generator import generate_features
except ImportError:
    # If running as submodule, try absolute import or rely on path
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from feature_generator import generate_features

# Load error model once
error_model = None
if os.path.exists(config.ERROR_MODEL_FILE):
    try:
        error_model = joblib.load(config.ERROR_MODEL_FILE)
        print("✅ 误差修正模型已成功加载。")
    except Exception as e:
        print(f"⚠️ 加载误差修正模型失败: {e}")

def load_model(ticker: str, add_log_func):
    model_path = config.get_model_path(ticker)
    if not os.path.exists(model_path):
        add_log_func(f"警告: 未找到模型文件 {model_path}")
        return None, None
    
    try:
        model_payload = joblib.load(model_path)
        
        # Consistent model loading logic
        model = None
        model_features = []

        if isinstance(model_payload, list):
            if model_payload and isinstance(model_payload[0], (RandomForestRegressor, lgb.LGBMRegressor)):
                model = model_payload[0]
                model_features = getattr(model, 'feature_names_in_', [])
            else:
                raise ValueError("List does not contain model object")
        elif isinstance(model_payload, (RandomForestRegressor, lgb.LGBMRegressor)):
            model = model_payload
            model_features = getattr(model, 'feature_names_in_', [])
        elif isinstance(model_payload, dict) and 'model' in model_payload and 'features' in model_payload:
            model = model_payload['model']
            model_features = model_payload['features']
        else:
            raise ValueError("Unknown model format")
            
        return model, model_features
    except Exception as e:
        add_log_func(f"加载模型失败 {model_path}: {e}")
        return None, None

def generate_signal_from_data(ticker: str, data_df: pd.DataFrame, add_log_func) -> dict:
    """Stock signal generation"""
    model, model_features = load_model(ticker, add_log_func)
    if not model:
        return {"ticker": ticker, "signal": "HOLD", "comment": "Model not found or invalid"}

    try:
        data_df['external_event'] = 0
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in data_df.columns:
                data_df[col] = pd.to_numeric(data_df[col], errors='coerce')
        
        features_df, feature_names = generate_features(data_df.copy())
        
        if features_df.empty or features_df.isna().all().all():
            add_log_func(f"错误: 为 {ticker} 生成特征后数据为空")
            return {"ticker": ticker, "signal": "HOLD", "comment": "Insufficient data"}
        
        if not model_features and feature_names:
            add_log_func("警告：模型中未找到 feature_names_in_，将使用 generate_features 返回的特征列表。")
            model_features = feature_names

        missing_features = [f for f in model_features if f not in features_df.columns]
        if missing_features:
            add_log_func(f"错误: 数据中缺少模型需要的特征: {missing_features}")
            return {"ticker": ticker, "signal": "HOLD", "comment": f"Missing features: {missing_features}"}
        
        last_day_features = features_df.iloc[-1:][model_features]
        
        base_prediction = model.predict(last_day_features)[0]
        final_prediction = base_prediction

        log_base_prediction(ticker, base_prediction)

        if error_model:
            try:
                error_model_input = pd.DataFrame({'base_prediction': [base_prediction]})
                predicted_error = error_model.predict(error_model_input)[0]
                final_prediction = base_prediction + predicted_error
                add_log_func(f"误差修正: 基础预测={base_prediction:.4f}, 预测误差={predicted_error:.4f}, 最终预测={final_prediction:.4f}")
            except Exception as e:
                add_log_func(f"应用误差模型失败: {e}")
        
        prediction_for_signal = final_prediction 
        
        signal = "HOLD"
        if prediction_for_signal > 0.005:
            signal = "BUY"
        elif prediction_for_signal < -0.005:
            signal = "SELL"
        
        add_log_func(f"为 {ticker} 生成信号: {signal} (最终预测值: {prediction_for_signal:.4f})")
        return {"ticker": ticker, "signal": signal, "prediction": prediction_for_signal}
    except Exception as e:
        import traceback
        add_log_func(f"generate_signal_from_data 错误: {e}")
        add_log_func(traceback.format_exc())
        return {"ticker": ticker, "signal": "ERROR", "comment": str(e)}

def generate_signal_from_crypto_data(ticker: str, data_df: pd.DataFrame, add_log_func) -> dict:
    """Crypto signal generation"""
    model, model_features = load_model(ticker, add_log_func)
    if not model:
        return {"ticker": ticker, "signal": "HOLD", "comment": "Model not found"}
    
    try:
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in data_df.columns:
                data_df[col] = pd.to_numeric(data_df[col], errors='coerce')
        
        features_df, feature_names = generate_features(data_df.copy())
        features_df['external_event'] = 0
        
        if not model_features and feature_names:
            add_log_func("警告：模型中未找到 feature_names_in_，将使用 generate_features 返回的特征列表。")
            model_features = feature_names

        missing_features = [f for f in model_features if f not in features_df.columns]
        if missing_features:
            add_log_func(f"错误: 数据中缺少模型需要的特征: {missing_features}")
            return {"ticker": ticker, "signal": "HOLD", "comment": f"Missing features: {missing_features}"}

        last_day_features = features_df.iloc[-1:][model_features]

        if last_day_features.isnull().values.any():
            add_log_func(f"警告: 用于预测的最新数据点包含NaN值")
            return {"ticker": ticker, "signal": "HOLD", "comment": "数据不足以生成所有特征 (NaNs in last row)"}
            
        prediction = model.predict(last_day_features)[0]
        add_log_func(f"模型预测值 (原始): {prediction:.6f}")
        
        signal = "HOLD"
        if prediction > 0.005:
            signal = "BUY"
        elif prediction < -0.005:
            signal = "SELL"

        add_log_func(f"为 {ticker} 生成信号: {signal} (模型预测值: {prediction:.4f})")
        return {"ticker": ticker, "signal": signal, "prediction": prediction}

    except Exception as e:
        import traceback
        add_log_func(f"generate_signal_from_crypto_data 错误: {e}")
        add_log_func(traceback.format_exc())
        return {"ticker": ticker, "signal": "ERROR", "comment": str(e)}
