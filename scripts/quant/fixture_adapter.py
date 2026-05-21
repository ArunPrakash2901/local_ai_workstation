from typing import List, Dict, Any
from datetime import datetime, timedelta
from .adapters import OHLCVProvider

class FixtureAdapter(OHLCVProvider):
    """A deterministic local fixture adapter for testing ingestion pipelines."""

    @property
    def provider_name(self) -> str:
        return "fixture"

    @property
    def supported_modes(self) -> List[str]:
        return ["research", "test"]

    def fetch_ohlcv(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime, 
        interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """Return hard-coded synthetic OHLCV data for SPY."""
        if symbol.upper() != "SPY":
            return []

        # Synthetic fixture data (5 days)
        # Clearly fake but valid OHLCV
        base_price = 450.0
        data = []
        
        # Ensure we don't return data outside the requested range
        current = start_date
        if current > datetime(2026, 5, 20): # Fixed range for fixture
            return []

        for i in range(5):
            ts = datetime(2026, 5, 15) + timedelta(days=i)
            if ts < start_date or ts > end_date:
                continue
                
            data.append({
                "timestamp": ts.isoformat(),
                "open": base_price + i,
                "high": base_price + i + 2,
                "low": base_price + i - 1,
                "close": base_price + i + 0.5,
                "volume": 1000000 + (i * 1000),
                "metadata": {
                    "synthetic": True,
                    "test_only": True,
                    "provider": "fixture"
                }
            })
        
        return data
