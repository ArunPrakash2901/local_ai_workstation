import math

def validate_synthetic_price_fixture(data):
    if not isinstance(data, dict):
        raise ValueError("Fixture must be a dictionary")
        
    if not data.get('synthetic_fixture'):
        raise ValueError("Fixture must explicitly declare synthetic_fixture: true")
        
    if not data.get('not_market_data'):
        raise ValueError("Fixture must explicitly declare not_market_data: true")
        
    if not data.get('not_strategy_result'):
        raise ValueError("Fixture must explicitly declare not_strategy_result: true")
        
    rows = data.get('rows', [])
    if not rows:
        raise ValueError("Fixture contains no rows")
        
    for i, row in enumerate(rows):
        if 'timestamp' not in row or 'close' not in row:
            raise ValueError(f"Row {i} missing required fields 'timestamp' or 'close'")
        if not isinstance(row['close'], (int, float)):
            raise ValueError(f"Row {i} close price must be numeric")
            
    return True

def compute_simple_returns(rows):
    returns = []
    for i in range(1, len(rows)):
        prev_close = rows[i-1]['close']
        curr_close = rows[i]['close']
        if prev_close == 0:
            returns.append(0)
        else:
            returns.append((curr_close - prev_close) / prev_close)
    return returns

def run_synthetic_no_strategy_smoke_test(rows, initial_capital=10000):
    returns = compute_simple_returns(rows)
    equity = [initial_capital]
    
    for r in returns:
        equity.append(equity[-1] * (1 + r))
        
    return {
        "is_real_strategy": False,
        "is_synthetic_fixture": True,
        "returns": returns,
        "equity_curve": equity
    }

def compute_basic_result_metrics(equity_curve):
    if not equity_curve or len(equity_curve) < 2:
        return {"total_return": 0, "max_drawdown": 0}
        
    initial = equity_curve[0]
    final = equity_curve[-1]
    total_return = (final - initial) / initial
    
    peak = equity_curve[0]
    max_dd = 0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        if dd > max_dd:
            max_dd = dd
            
    return {
        "total_return": total_return,
        "max_drawdown": max_dd
    }
