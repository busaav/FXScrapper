from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from data_config import MONTOS_POR_MONEDA

# Esta clase solo define la estructura y el manejo básico.
class BaseScraper:
    def __init__(self, driver, competidor_nombre, url_base):
        self.driver = driver
        self.nombre = competidor_nombre
        self.url_base = url_base

    # Este método debe ser implementado OBLIGATORIAMENTE en cada clase específica.
    def get_tasa_por_ruta(self, ruta):
        """
        Método que ejecuta la lógica de scraping específica.
        Debe devolver (tasa_directa: float, monto_cotizado: str).
        """
        raise NotImplementedError(
            f"El método get_tasa_por_ruta debe ser implementado en {self.nombre}Scraper."
        )

    def _get_monto_a_cotizar(self, moneda_origen):
        """Función auxiliar para obtener el monto basado en la moneda."""
        return MONTOS_POR_MONEDA.get(moneda_origen, "100")