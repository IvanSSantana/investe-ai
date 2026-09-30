class ScrapingError(Exception):
    """Exception raised for errors that occur during web scraping."""
    ...

class NoDataForExportError(Exception):
    """Exception raised when there is no data available for export (CSV, Excel, etc.)."""
    ...

class PDFDownloadFailedException(Exception):
    """Exception raised when no valid PDFs could be downloaded or located on disk for a given ticker."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        super().__init__(f"No valid PDF reports found or downloaded for ticker '{ticker}'.")