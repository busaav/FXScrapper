from scrapers.base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import re
import time
from data_config import URLS_COMPETIDORES

class MoneyGramScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "Money Gram", "https://www.moneygram.com/mgo/us/en/")
        
        # 1. Mapeo de Origen -> URL Regional de MoneyGram
        self.url_map = {
            "CLP": "https://www.moneygram.com/mgo/cl/es", # Chile
            "EUR": "https://www.moneygram.com/mgo/es/es", # España (para Euro)
            "BRL": "https://www.moneygram.com/mgo/br/pt", # Brasil
            "USD": "https://www.moneygram.com/mgo/us/en", # USA
            "GBP": "https://www.moneygram.com/mgo/gb/en", # UK
            "COP": "https://www.moneygram.com/mgo/co/es", # Colombia (si soporta envío)
            "PEN": "https://www.moneygram.com/mgo/pe/es"  # Perú (si soporta envío)
        }
        
        # 2. Mapeo de Moneda Destino -> Nombre del País (para el buscador)
        # Es importante poner el nombre en el idioma de la URL de origen (Español/Portugués)
        self.destination_map = {
            "VES": "Venezuela",
            "COP": "Colombia",
            "ARS": "Argentina",
            "PEN": "Perú",
            "BRL": "Brasil",
            "CLP": "Chile",
            "USD": "Estados Unidos",
            "EUR": "España",
            "MXN": "México"
        }

    def _cerrar_cookies(self):
        """Cierra el banner de cookies si aparece"""
        try:
            xpaths = [
                "//button[contains(@id, 'onetrust-accept')]",
                "//button[contains(text(), 'Aceptar cookies')]",
                "//button[contains(text(), 'Aceitar')]", # Portugués
                "//button[contains(text(), 'Allow All')]"
            ]
            for xp in xpaths:
                try:
                    btn = self.driver.find_element(By.XPATH, xp)
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(1)
                        break
                except: pass
        except: pass

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        # Determinar URL y Nombre de País Destino
        url = self.url_map.get(moneda_origen, "https://www.moneygram.com/mgo/us/en")
        pais_destino = self.destination_map.get(moneda_destino, "Venezuela") # Default Venezuela si falla
        
        # Ajuste de idioma para Brasil (nombres en portugués)
        if moneda_origen == "BRL":
            if pais_destino == "Venezuela": pais_destino = "Venezuela" # Igual
            if pais_destino == "Colombia": pais_destino = "Colômbia"
            if pais_destino == "Perú": pais_destino = "Peru"
        
        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        try:
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 20)
            time.sleep(5) 

            self._cerrar_cookies()

            # 1. INGRESAR MONTO (Input id="sendAmount")
            try:
                input_monto = wait.until(EC.visibility_of_element_located((By.ID, "sendAmount")))
                input_monto.clear()
                input_monto.send_keys(monto_a_cotizar)
                time.sleep(1)
            except Exception as e:
                print(f"    ⚠️ No se encontró campo de monto (puede que el país no permita envío online).")
                return 0.0, monto_a_cotizar

            # 2. SELECCIONAR PAÍS DESTINO (Input id="receiverCountry")
            try:
                input_pais = self.driver.find_element(By.ID, "receiverCountry")
                input_pais.click()
                time.sleep(0.5)
                
                # Escribir nombre del país
                input_pais.send_keys(pais_destino)
                time.sleep(2) 
                
                # Seleccionar de la lista
                # Buscamos el elemento que contenga el nombre exacto
                xpath_opcion = f"//li[contains(., '{pais_destino}')] | //div[@role='option']//div[contains(., '{pais_destino}')]"
                opcion = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_opcion)))
                opcion.click()
                print(f"    -> País destino seleccionado: {pais_destino}")
                
            except Exception as e:
                print(f"    ⚠️ Error seleccionando país {pais_destino}: {e}")
                return 0.0, monto_a_cotizar

            print("    -> Esperando estimación...")
            time.sleep(5) 

            # 3. EXTRAER TASA
            tasa_final = 0.0
            
            # Estrategia A: Texto directo "1 CLP = X.XXX ARS"
            try:
                # Buscamos textos que tengan el formato de tasa
                xpath_tasa = f"//*[contains(text(), '1 {moneda_origen}') and contains(text(), '=')]"
                elementos = self.driver.find_elements(By.XPATH, xpath_tasa)
                
                for el in elementos:
                    texto = el.text.strip()
                    # Regex para sacar el número de la derecha
                    match = re.search(r'=\s*([\d\.,]+)', texto)
                    if match:
                        val_str = match.group(1).replace(',', '.')
                        # Limpieza si hay puntos de miles (ej: 1.000.50)
                        if val_str.count('.') > 1: val_str = val_str.replace('.', '', val_str.count('.') - 1)
                        
                        tasa_final = float(val_str)
                        print(f"    ✅ Tasa encontrada (Texto): {tasa_final}")
                        break
            except: pass

            # Estrategia B: Cálculo por Inputs (sendAmount vs receiveAmount)
            if tasa_final == 0:
                try:
                    input_recibo = self.driver.find_element(By.ID, "receiveAmount")
                    val_recibo = input_recibo.get_attribute("value")
                    
                    if val_recibo:
                        num_recibo = float(re.sub(r'[^\d\.]', '', val_recibo.replace(',','.')))
                        num_envio = float(monto_a_cotizar)
                        if num_recibo > 0:
                            tasa_final = num_recibo / num_envio
                            print(f"    🧮 Tasa calculada: {tasa_final:.6f}")
                except Exception as e:
                    print(f"    ⚠️ Falló cálculo: {e}")

            if tasa_final > 0:
                return tasa_final, monto_a_cotizar

            print("    ❌ No se obtuvo tasa.")
            return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en MoneyGram: {e}")
            return 0.0, monto_a_cotizar