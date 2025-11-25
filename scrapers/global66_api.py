import requests
from .base_scraper import BaseScraper
from data_config import URLS_COMPETIDORES, MONTOS_POR_MONEDA

class Global66ApiScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "Global66", URLS_COMPETIDORES.get("Global66", ""))
        self.api_url = "https://api.global66.com/quote/public"
        
        # Mapeo de IDs de Ruta (Country/Currency ID)
        self.route_ids = {
            "CLP": 134, # Chile
            "PEN": 227, # Perú
            "COP": 137, # Colombia
            "ARS": 86,  # Argentina
            "VES": 266, # Venezuela
            "EUR": 36,  # España
            "USD": 59,  # Estados Unidos
            "US": 59,   # Alias
            "BRL": 117, # Brasil
            "MXN": 210  # México
        }

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando Global66 (API) para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        origin_id = self.route_ids.get(moneda_origen)
        dest_id = self.route_ids.get(moneda_destino)
        
        if not origin_id or not dest_id:
            print(f"    ❌ Error ID: No hay ID para {moneda_origen} o {moneda_destino}")
            return 0.0, "100"

        monto_str = self._get_monto_a_cotizar(moneda_origen)
        try:
            monto_clean = float(monto_str.replace('.', '').replace(',', '.'))
        except:
            monto_clean = 1000.0

        params = {
            "originRoute": origin_id,
            "destinationRoute": dest_id,
            "amount": monto_clean,
            "way": "origin",
            "paymentType": "WIRE_TRANSFER"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Origin": "https://www.global66.com",
            "Referer": "https://www.global66.com/"
        }
        
        try:
            response = requests.get(self.api_url, params=params, headers=headers, timeout=10)
            
            if response.status_code != 200:
                # Si falla (como en los 404 de EUR), reportamos pero no rompemos el flujo
                print(f"    ❌ API Status {response.status_code}: Ruta no disponible o error.")
                return 0.0, str(monto_clean)
                
            data = response.json()
            
            # 1. Verificar si existe el objeto contenedor 'quoteData'
            if 'quoteData' in data:
                # La estructura es: data['quoteData']['destinationAmount']
                quote_data = data['quoteData']
                valor_recibido = float(quote_data.get('destinationAmount', 0))
                
                if valor_recibido > 0:
                    tasa = valor_recibido / monto_clean
                    print(f"    ✅ Éxito: {monto_clean} {moneda_origen} -> {valor_recibido} {moneda_destino} (Tasa: {tasa:.6f})")
                    return tasa, str(monto_clean)
            
            # 2. Intentos de fallback por si la API cambia de formato (estructuras antiguas)
            elif 'amountDestiny' in data:
                valor_recibido = float(data['amountDestiny'])
                if valor_recibido > 0:
                    tasa = valor_recibido / monto_clean
                    print(f"    ✅ Éxito (Legacy): {tasa:.6f}")
                    return tasa, str(monto_clean)
                    
            print(f"    ⚠️ JSON recibido pero estructura desconocida: {str(data)[:100]}...")
            return 0.0, str(monto_clean)

        except Exception as e:
            print(f"    ❌ Excepción de conexión: {e}")
            return 0.0, str(monto_clean)