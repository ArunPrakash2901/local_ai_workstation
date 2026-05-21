from typing import Protocol, List, Dict, Any, Optional
from datetime import datetime

class OHLCVProvider(Protocol):
    """Protocol for OHLCV data adapters."""
    
    @property
    def provider_name(self) -> str:
        ...

    @property
    def supported_modes(self) -> List[str]:
        ...

    def fetch_ohlcv(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime, 
        interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        """Fetch OHLCV data for a given symbol and date range."""
        ...
