class ScrapingError(Exception):
    """Exceção para erros relacionados à raspagem de dados."""
    ...

class NoDataForExportError(Exception):
    """Exceção para indicar que não há dados disponíveis para a geração do arquivo de exportação (CSV, Excel, etc.)."""
    ...