from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import re
import time
from data_config import URLS_COMPETIDORES

class RiaScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "RIA", URLS_COMPETIDORES.get("RIA", "https://www.riamoneytransfer.com/es-es/"))
        
        self.country_map = {
            "ARS": "Argentina",
            "COP": "Colombia",
            "PEN": "Perú",
            "USD": "Estados Unidos",
            "VES": "Venezuela",
            "MXN": "México",
            "BRL": "Brasil",
            "CLP": "Chile"
        }

    def _clean_amount(self, value_str):
        """Limpia el string detectando si es formato 1,000.00 (US) o 1.000,00 (EU)."""
        if not value_str: return 0.0
        # Eliminar símbolos de moneda y espacios
        clean = re.sub(r'[^\d\.,]', '', str(value_str))
        if not clean: return 0.0

        # Lógica de detección por posición del último separador
        if ',' in clean and '.' in clean:
            last_dot = clean.rfind('.')
            last_comma = clean.rfind(',')
            
            if last_dot > last_comma: 
                # Formato US: 82,300.30 (El punto está al final)
                clean = clean.replace(',', '') # Quitar comas de miles
            else: 
                # Formato EU: 82.300,30 (La coma está al final)
                clean = clean.replace('.', '').replace(',', '.')
                
        elif ',' in clean:
            # Solo comas (ej: 50,00 o 1,000).
            # En RIA España, coma suele ser decimal.
            clean = clean.replace(',', '.')
            
        elif '.' in clean:
            # Solo puntos (ej: 50.00 o 1.000).
            # Si tiene 3 decimales exactos, asumimos que es un separador de miles (ej: 82.300)
            parts = clean.split('.')
            if len(parts) > 1 and len(parts[-1]) == 3:
                clean = clean.replace('.', '') # Es miles
            # Si no, asumimos es punto decimal estándar
        
        try: return float(clean)
        except: return 0.0

    def _cerrar_cookies(self):
        try:
            btn = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
            btn.click()
            time.sleep(1)
        except: pass

    def _seleccionar_destino(self, moneda_destino):
        pais_nombre = self.country_map.get(moneda_destino)
        if not pais_nombre: return False

        print(f"    -> Buscando destino: {pais_nombre}...")
        try:
            wait = WebDriverWait(self.driver, 15)
            
            try:
                search_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder*='país'], input[placeholder*='Country']")
            except:
                dropdown = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "dropdown-container")))
                dropdown.click()
                time.sleep(0.5)
                search_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")

            search_input.click()
            search_input.clear()
            search_input.send_keys(pais_nombre)
            time.sleep(1.5)
            search_input.send_keys(Keys.ENTER)
            
            try:
                opcion = self.driver.find_element(By.XPATH, f"//li[contains(., '{pais_nombre}')]")
                if opcion.is_displayed():
                    opcion.click()
            except: pass

            time.sleep(3)
            return True

        except Exception as e:
            print(f"      ⚠️ Error seleccionando destino: {e}")
            return False

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        if moneda_origen != "EUR":
            print(f"    ⛔ RIA configurado solo para origen EUR.")
            return 0.0, "0"

        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        try:
            self.driver.get(self.url_base)
            wait = WebDriverWait(self.driver, 20)
            time.sleep(5) 
            self._cerrar_cookies()

            # 1. SELECCIONAR DESTINO
            if not self._seleccionar_destino(moneda_destino):
                return 0.0, monto_a_cotizar

            # 2. INGRESAR MONTO
            try:
                input_envio = self.driver.find_element(By.ID, "sending-amount")
                actions = ActionChains(self.driver)
                actions.click(input_envio)
                actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL)
                actions.send_keys(Keys.BACK_SPACE)
                actions.perform()
                time.sleep(0.5)
                input_envio.send_keys(monto_a_cotizar)
                self.driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(4)
            except: pass

            # 3. EXTRAER TASA
            tasa_final = 0.0
            
            # A) Cálculo por Inputs (Prioridad)
            try:
                input_recibo = self.driver.find_element(By.ID, "receiving-amount")
                val_recibo = input_recibo.get_attribute("value")
                
                if val_recibo:
                    n_out = self._clean_amount(val_recibo)
                    n_in = float(monto_a_cotizar)
                    
                    if n_out > 0:
                        tasa_final = n_out / n_in
                        print(f"    🧮 Tasa calculada ({n_out} / {n_in}): {tasa_final:.6f}")
            except Exception as e:
                print(f"    ⚠️ Falló cálculo inputs: {e}")

            # B) Texto (Fallback)
            if tasa_final == 0:
                try:
                    elementos = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Tasa')]")
                    for el in elementos:
                        match = re.search(r'([\d\.,]+)', el.text.replace('Tasa', ''))
                        if match:
                            val = self._clean_amount(match.group(1))
                            if val > 0:
                                tasa_final = val
                                print(f"    ✅ Tasa leída de texto: {tasa_final}")
                                break
                except: pass

            return tasa_final, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en RIA: {e}")
            return 0.0, monto_a_cotizar