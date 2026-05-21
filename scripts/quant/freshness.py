from datetime import datetime, timedelta
from typing import Any, Dict, Optional

def check_freshness(latest_timestamp: datetime, freshness_policy: str, current_time: Optional[datetime] = None) -> Dict[str, Any]:
    """Check if the latest data timestamp meets the freshness policy."""
    if current_time is None:
        current_time = datetime.now()
    
    # Parse policy (e.g., "max_lag_24h")
    max_lag_hours = 24
    if freshness_policy.startswith("max_lag_"):
        try:
            val = freshness_policy.replace("max_lag_", "")
            if val.endswith("h"):
                max_lag_hours = int(val[:-1])
            elif val.endswith("d"):
                max_lag_hours = int(val[:-1]) * 24
        except ValueError:
            pass # Use default 24h

    max_allowed_lag = timedelta(hours=max_lag_hours)
    actual_lag = current_time - latest_timestamp
    
    is_stale = actual_lag > max_allowed_lag
    
    return {
        "ok": not is_stale,
        "stale": is_stale,
        "latest_observed_timestamp": latest_timestamp.isoformat(),
        "current_timestamp": current_time.isoformat(),
        "actual_lag_hours": actual_lag.total_seconds() / 3600,
        "max_allowed_lag_hours": max_lag_hours,
        "errors": [],
        "warnings": []
    }
