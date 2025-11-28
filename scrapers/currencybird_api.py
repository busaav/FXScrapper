import requests
from .base_scraper import BaseScraper
from data_config import URLS_COMPETIDORES

class CurrencyBirdApiScraper(BaseScraper):
    def __init__(self, driver):
        # El driver no se usa en API, pero se mantiene por compatibilidad
        super().__init__(driver, "CurrencyBird", "https://www.currencybird.cl/")
        
        # Endpoint de la API
        self.api_url = "https://services.prod.currencybird.cl/apigateway-cb/api/public/quotes/"
        
        # Mapeo de Moneda -> Código de País (ISO 2) para la API
        # CurrencyBird requiere tanto la moneda como el país.
        self.country_codes = {
            "CLP": "CL",
            "ARS": "AR",
            "COP": "CO",
            "PEN": "PE",
            "USD": "US",
            "EUR": "ES", # Usamos España (ES) como país representativo para Euro
            "BRL": "BR",
            "MXN": "MX"
        }

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} (API) para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        # CurrencyBird solo opera desde Chile (CLP)
        if moneda_origen != "CLP":
            print("    ⛔ CurrencyBird solo permite origen CLP.")
            return 0.0, "0"

        # Obtener códigos de país
        pais_origen = self.country_codes.get(moneda_origen)
        pais_destino = self.country_codes.get(moneda_destino)
        
        if not pais_origen or not pais_destino:
            print(f"    ⚠️ No hay código de país mapeado para {moneda_origen} o {moneda_destino}")
            return 0.0, "0"

        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        # Parámetros de la API
        params = {
            "amount": monto_a_cotizar,
            "quoteType": "sell",
            "originCountry": pais_origen,
            "originCurrency": moneda_origen,
            "destinationCountry": pais_destino,
            "destinationCurrency": moneda_destino
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(self.api_url, params=params, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"    ❌ API Error {response.status_code}: {response.text}")
                return 0.0, monto_a_cotizar
            
            data = response.json()
            
            # La API devuelve "value" (lo que recibe) y "originValue" (lo que envías)
            # Ejemplo: {"value": 154575.13, "originValue": 100000, ...}
            
            if "value" in data and data["value"] is not None:
                valor_recibido = float(data["value"])
                monto_enviado = float(monto_a_cotizar)
                
                if valor_recibido > 0:
                    # Calculamos la tasa implícita real
                    tasa_directa = valor_recibido / monto_enviado
                    
                    # También podríamos usar data['inverseExchangeRate'] si preferimos la oficial,
                    # pero calcularla asegura que incluimos cualquier comisión oculta en el monto final.
                    print(f"    ✅ Tasa API encontrada: {tasa_directa:.6f} (Recibe: {valor_recibido})")
                    return tasa_directa, monto_a_cotizar
            
            print(f"    ⚠️ Respuesta inesperada: {data}")
            return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Excepción conectando a API: {e}")
            return 0.0, monto_a_cotizar