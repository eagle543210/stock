# Refactor Log

## Summary
Refactoring of `api.py` and introduction of Service Layer to address "God Object" anti-pattern and improve performance/maintainability.

## Changes

### 1. Configuration Centralization
- **Created `config.py`**: Centralized environment variables (API Keys), file paths, and model configurations.
- **Benefit**: Easier management of settings, reduced hardcoding.

### 2. Service Layer Introduction (`services/`)
- **`services/model_service.py`**: Encapsulates model loading, feature generation, and signal inference logic.
    - Moves heavy logic out of `api.py`.
    - Unifies logic for Stock and Crypto signal generation.
- **`services/trading_service.py`**: Encapsulates Binance trading logic using `ccxt`.
    - **Async Support**: Fully asynchronous using `ccxt.async_support` to prevent blocking the API.
    - Replaces custom `binance_http_client.py`.
- **`services/data_service.py`**: Handles logging and audit trail writing.

### 3. API Optimization (`api.py`)
- **Slimmed Down**: `api.py` now focuses on Routing and Request handling.
- **Non-Blocking**: CPU-intensive tasks (Model Inference) are now run in `asyncio` executors.
- **Unified Interface**: Integrates the new services.

### 4. Cleanup
- **Deleted `binance_http_client.py`**: Removed redundant custom implementation in favor of the industry-standard `ccxt` library.

## Next Steps
- **Validation**: Test `get_btc_signal` endpoint with Testnet keys to verify `ccxt` integration.
- **Legacy Cleanup**: Further verify `trader.py` (MT5 wrapper) integration.
