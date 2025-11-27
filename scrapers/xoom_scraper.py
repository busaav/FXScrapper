from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import re
import time
from data_config import URLS_COMPETIDORES

class XoomScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "XOOM", "https://www.xoom.com/")
        
        self.country_slugs = {
            "ARS": "argentina",
            "COP": "colombia",
            "PEN": "peru",
            "USD": "united-states",
            "MXN": "mexico",
            "BRL": "brazil",
            "VES": "venezuela"
        }

    def _clean_amount(self, value_str):
        if not value_str: return 0.0
        clean = re.sub(r'[^\d\.,]', '', str(value_str))
        try:
            # Xoom usa formato US (1,000.00) en la versión internacional
            return float(clean.replace(',', ''))
        except:
            return 0.0

    def _cerrar_cookies(self):
        try:
            xpath = "//button[contains(text(), 'Accept') or contains(text(), 'Aceptar')]"
            btn = self.driver.find_element(By.XPATH, xpath)
            btn.click()
            time.sleep(1)
        except: pass

    def _cambiar_origen_a_eur(self):
        print("    -> Verificando moneda de origen...")
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # Buscar botón del selector
            xpath_picker = "//button[contains(@id, 'source-currency-picker')]"
            picker_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_picker)))
            
            if "EUR" in picker_btn.text:
                print("      ✅ Origen ya es EUR.")
                return True
            
            print(f"      -> Cambiando de {picker_btn.text} a EUR...")
            picker_btn.click()
            time.sleep(1)
            
            # Seleccionar EUR
            xpath_eur = "//li[contains(., 'EUR')] | //button[contains(., 'EUR')] | //div[contains(text(), 'EUR')]"
            opcion_eur = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_eur)))
            opcion_eur.click()
            
            time.sleep(4) # Esperar recarga
            print("      ✅ Origen cambiado a EUR.")
            return True

        except Exception as e:
            print(f"      ⚠️ No se pudo cambiar origen a EUR: {e}")
            return False

    def _ingresar_monto_robusto(self, monto):
        """Ingresa el monto forzando el valor con JS."""
        print(f"    -> Ingresando monto: {monto}...")
        try:
            wait = WebDriverWait(self.driver, 15)
            # Buscamos por el ID estable que se ve en tu captura
            input_envio = wait.until(EC.presence_of_element_located((By.ID, "text-input-send-input")))
            
            # Inyección directa de valor (Bypass de validaciones de teclado)
            self.driver.execute_script("arguments[0].value = '';", input_envio)
            self.driver.execute_script(f"arguments[0].value = '{monto}';", input_envio)
            
            # Disparar eventos para que la web reaccione
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_envio)
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", input_envio)
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));", input_envio)
            
            time.sleep(1)
            
            # Clic fuera para asegurar
            self.driver.find_element(By.TAG_NAME, "body").click()
            return True
            
        except Exception as e:
            print(f"      ⚠️ Error crítico ingresando monto: {e}")
            return False

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        slug = self.country_slugs.get(moneda_destino)
        if not slug:
            return 0.0, "100"

        url = f"https://www.xoom.com/{slug}/send-money"
        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        try:
            self.driver.get(url)
            time.sleep(4)
            self._cerrar_cookies()

            if moneda_origen == "EUR":
                self._cambiar_origen_a_eur()

            # Usar la función robusta con JS
            self._ingresar_monto_robusto(monto_a_cotizar)

            print("    -> Esperando cálculo...")
            time.sleep(4)

            tasa_final = 0.0
            try:
                # Buscar el elemento con data-testid
                elemento_tasa = self.driver.find_element(By.CSS_SELECTOR, "[data-testid='fx-rate-comparison-string']")
                texto = elemento_tasa.text
                
                match = re.search(r'=\s*([\d\.,]+)', texto)
                if match:
                    val_str = match.group(1)
                    val_clean = val_str.replace(',', '')
                    try:
                        tasa_final = float(val_clean)
                    except:
                        tasa_final = float(val_str.replace('.', '').replace(',', '.'))

                    print(f"    ✅ Tasa encontrada: {tasa_final} (Raw: {texto})")
            except Exception as e:
                print(f"    ⚠️ Error extrayendo tasa: {e}")

            if tasa_final > 0:
                return tasa_final, monto_a_cotizar

            return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en XOOM: {e}")
            return 0.0, monto_a_cotizar