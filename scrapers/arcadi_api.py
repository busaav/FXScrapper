import requests
from .base_scraper import BaseScraper
from data_config import URLS_COMPETIDORES, MONTOS_POR_MONEDA

class ArcadiApiScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "Arcadi", URLS_COMPETIDORES.get("Arcadi", ""))
        self.api_url = "https://www.arcadienvios.com/api/v2/exchange_rates"
        
        # Mapeo de Moneda -> ID de País (según tu JSON)
        self.country_ids = {
            "CLP": 9,  # Chile
            "COP": 2,  # Colombia
            "VES": 1,  # Venezuela
            "USD": 7,  # Estados Unidos
            "US": 7,   # Alias para USD
            "EUR": 6,  # España (Asumimos ID 6 para Euro)
            "PEN": 8,  # Perú
            "BRL": 5,  # Brasil
            "EC": 3,   # Ecuador
        }

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando Arcadi (API) para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        # Obtener IDs
        source_id = self.country_ids.get(moneda_origen)
        dest_id = self.country_ids.get(moneda_destino)
        
        if not source_id or not dest_id:
            print(f"    ❌ Error: No hay ID de país para {moneda_origen} o {moneda_destino}")
            return 0.0, "100"

        monto_str = self._get_monto_a_cotizar(moneda_origen)
        
        # Parámetros de la URL
        params = {
            "source_country_id": source_id,
            "destination_country_id": dest_id
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(self.api_url, params=params, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"    ❌ Error API {response.status_code}: {response.text}")
                return 0.0, monto_str
                
            data = response.json()
            
            # Corrección basada en tus logs:
            # La estructura es {'VES': [{'rate': '0.3545', ...}]}
            
            # Ajuste para moneda destino (ej: US -> USD)
            target_key = moneda_destino
            if target_key == "US":
                target_key = "USD"
            
            tasa = 0.0
            
            # Buscamos la lista usando la clave de la moneda destino
            if target_key in data and isinstance(data[target_key], list) and len(data[target_key]) > 0:
                item = data[target_key][0] # Tomamos el primer elemento de la lista
                if 'rate' in item:
                    tasa = float(item['rate'])
            
            if tasa > 0:
                print(f"    ✅ Tasa encontrada: {tasa}")
                return tasa, monto_str
            
            print(f"    ⚠️ Estructura inesperada para {target_key}: {str(data)[:100]}...")
            return 0.0, monto_str

        except Exception as e:
            print(f"    ❌ Excepción: {e}")
            return 0.0, monto_str