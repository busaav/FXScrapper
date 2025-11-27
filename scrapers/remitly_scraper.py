from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import re
import time
from data_config import URLS_COMPETIDORES

class RemitlyScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "Remitly", URLS_COMPETIDORES.get("Remitly", "https://www.remitly.com/"))

    def _clean_amount(self, value_str):
        """Limpia el monto considerando formato europeo (1.000,00) o americano."""
        if not value_str: return 0.0
        clean = re.sub(r'[^\d\.,]', '', str(value_str))
        
        if ',' in clean and '.' in clean:
            if clean.rindex(',') > clean.rindex('.'): # 1.000,50
                clean = clean.replace('.', '').replace(',', '.')
            else: # 1,000.50
                clean = clean.replace(',', '')
        elif ',' in clean:
            # Asumimos coma decimal para Remitly España
            clean = clean.replace(',', '.')
        
        try: return float(clean)
        except: return 0.0

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        # Validación de origen
        if moneda_origen != "EUR":
            print("    ⛔ Este scraper está configurado para origen EUR (España).")
            return 0.0, "0"

        # Construcción de URL
        # Ej: https://www.remitly.com/es/es/currency-converter/eur-to-usd-rate
        url = f"https://www.remitly.com/es/es/currency-converter/{moneda_origen.lower()}-to-{moneda_destino.lower()}-rate"
        
        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        try:
            self.driver.get(url)
            wait = WebDriverWait(self.driver, 15)
            time.sleep(4) # Espera carga

            # 1. COOKIES (Botón "Aceptar cookies" o similar)
            try:
                btn_cookie = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Aceptar') or contains(text(), 'Accept')]")
                btn_cookie.click()
                time.sleep(1)
            except: pass

            # 2. INGRESAR MONTO
            # Buscamos el input que contiene "env" o "send" en su ID dinámico
            # O el primer input numérico visible
            try:
                input_envio = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[id*='flag-input'][id*='env']")))
                
                # Borrado humano
                input_envio.click()
                actions = ActionChains(self.driver)
                actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                time.sleep(0.1)
                actions.send_keys(Keys.BACK_SPACE).perform()
                
                input_envio.send_keys(monto_a_cotizar)
                self.driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(3) # Esperar cálculo
            except Exception as e:
                print(f"    ⚠️ Error ingresando monto: {e}")

            # 3. EXTRAER TASA
            tasa_final = 0.0
            
            # Estrategia A: Texto "1 EUR = X.XX USD"
            # En tus capturas se ve un div que dice "1 EUR = 1,1386 USD"
            try:
                # Buscamos texto que tenga formato de tasa
                elementos_tasa = self.driver.find_elements(By.XPATH, "//*[contains(text(), '1 EUR =')]")
                for el in elementos_tasa:
                    texto = el.text.strip()
                    match = re.search(r'=\s*([\d\.,]+)', texto)
                    if match:
                        val = self._clean_amount(match.group(1))
                        if val > 0:
                            tasa_final = val
                            print(f"    ✅ Tasa encontrada (Texto): {tasa_final}")
                            break
            except: pass

            # Estrategia B: Cálculo por Inputs
            if tasa_final == 0:
                try:
                    # Buscamos el input de recepción (contiene 'recibe' o 'recv' en ID)
                    input_recibo = self.driver.find_element(By.CSS_SELECTOR, "input[id*='flag-input'][id*='recibe']")
                    val_recibo = input_recibo.get_attribute("value")
                    
                    if val_recibo:
                        n_out = self._clean_amount(val_recibo)
                        n_in = float(monto_a_cotizar)
                        
                        if n_out > 0:
                            tasa_final = n_out / n_in
                            print(f"    🧮 Tasa calculada: {tasa_final:.6f}")
                except Exception as e:
                    print(f"    ⚠️ Falló cálculo inputs: {e}")

            if tasa_final > 0:
                return tasa_final, monto_a_cotizar

            return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en Remitly: {e}")
            return 0.0, monto_a_cotizar