import logging
from typing import Any
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

class YFinanceService:

    def get_monthly_summary(self, ticker: str, period: str = "1y") -> list[dict[str, Any]]:
        """
        Fetches historical data for a ticker and aggregates it into monthly summaries.

        Args:
            ticker (str): Asset ticker symbol (e.g. "HFOF11").
            period (str): History period for yfinance (default: "1y").

        Returns:
            list[dict[str, Any]]: List of monthly financial summaries.
        """
        formatted_ticker = f"{ticker.upper()}.SA" if not ticker.upper().endswith(".SA") else ticker.upper()

        logger.info(f"Fetching historical data for {formatted_ticker} with period={period}")
        ticker_obj = yf.Ticker(formatted_ticker)
        df = ticker_obj.history(period=period, actions=True)

        if df.empty:
            logger.warning(f"No historical data found for {formatted_ticker}")
            return []

        df = df.reset_index()
        df["YearMonth"] = df["Date"].dt.strftime("%Y-%m")

        monthly_data: list[dict[str, Any]] = []

        for ym, group in df.groupby("YearMonth"):
            group = group.sort_values("Date")

            initial_price = float(group["Close"].iloc[0])
            final_price = float(group["Close"].iloc[-1])

            price_var_percent = (
                ((final_price - initial_price) / initial_price) * 100.0 if initial_price > 0 else 0.0
            )

            dividends_paid = float(group["Dividends"].sum()) if "Dividends" in group.columns else 0.0
            dy_percent = (dividends_paid / initial_price) * 100.0 if initial_price > 0 else 0.0

            total_return_percent = price_var_percent + dy_percent

            monthly_data.append(
                {
                    "year_month": str(ym),
                    "initial_price": round(initial_price, 2),
                    "final_price": round(final_price, 2),
                    "price_variation_percent": round(price_var_percent, 2),
                    "dividends_paid": round(dividends_paid, 2),
                    "dividend_yield_percent": round(dy_percent, 2),
                    "total_return_percent": round(total_return_percent, 2),
                }
            )

        return monthly_data