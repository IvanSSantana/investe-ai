import logging
import requests

logger = logging.getLogger(__name__)

class MarketDataService:
    """Service to fetch dynamic macro economic data from official sources."""

    BCB_SELIC_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"

    def get_current_risk_free_rate(self, fallback_rate: float = 0.105) -> float:
        """Fetches current target Selic rate from Central Bank of Brazil API.

        Returns decimal representation (e.g., 0.1075 for 10.75%).
        """
        try:
            response = requests.get(self.BCB_SELIC_URL, timeout=15)
            
            if response.status_code != 200:
                logger.warning(
                    f"Failed to fetch Selic rate from BCB API. Status code: {response.status_code}. Using fallback rate: {fallback_rate}"
                )
                return fallback_rate

            data = response.json()
            
            selic_annual_percent = float(data[0]["valor"])
            rate_decimal = selic_annual_percent / 100.0
            
            logger.info(f"Successfully fetched current Risk-Free Rate (Selic): {selic_annual_percent}%")
            return rate_decimal
        except Exception as exc:
            logger.warning(
                f"Failed to fetch dynamic Selic rate from BCB API: {exc}. Using fallback rate: {fallback_rate}"
            )
            return fallback_rate