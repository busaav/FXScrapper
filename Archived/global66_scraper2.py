from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import time
from data_config import URLS_COMPETIDORES

class Global66Scraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "Global66", URLS_COMPETIDORES["Global66"])
        self.first_visit = True  #Flag para saber si es la primera visita

    def _wait_for_destination_value(self, driver, xpath):
        """Función auxiliar para esperar que el valor de destino se llene"""
        try:
            element = driver.find_element(By.XPATH, xpath)
            value = element.get_attribute("value")
            if not value:
                return False
            value_clean = re.sub(r'[^\d\.]', '', value.replace(',', ''))
            return value_clean and float(value_clean) > 0
        except (NoSuchElementException, ValueError):
            return False

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3] 
        moneda_destino = ruta[3:]
        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        self.driver.get(self.url_base)
        wait = WebDriverWait(self.driver, 30)
        
        # Si es la primera visita, refrescar para eliminar el pop-up
        if self.first_visit:
            print("    -> Primera visita detectada, refrescando para eliminar pop-up...")
            time.sleep(3)  # Esperar a que la página y el pop-up carguen
            self.driver.refresh()
            print("    -> Página refrescada, pop-up eliminado ✅")
            time.sleep(2)  # Esperar a que la página se recargue
            self.first_visit = False  # Marcar que ya no es la primera visita

        try:
            # 1. Seleccionar Moneda de Origen
            print(f"    -> Seleccionando moneda origen: {moneda_origen}")
            selector_origen_multiselect = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".multiselect.country-vmultiselect:not(.destiny)"))
            )
            selector_origen_multiselect.click()
            
            xpath_moneda_origen = f"//span[contains(text(), '{moneda_origen}')]"
            wait.until(EC.element_to_be_clickable((By.XPATH, xpath_moneda_origen))).click()
            time.sleep(1)
            
            # 2. Seleccionar Moneda de Destino
            print(f"    -> Seleccionando moneda destino: {moneda_destino}")
            selector_destino_multiselect = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".multiselect.country-vmultiselect.destiny"))
            )
            selector_destino_multiselect.click()
            
            xpath_moneda_destino = f"//span[contains(text(), '{moneda_destino}')]"
            wait.until(EC.element_to_be_clickable((By.XPATH, xpath_moneda_destino))).click()
            time.sleep(1)
            
            # 3. Ingresar el Monto
            print(f"    -> Ingresando monto: {monto_a_cotizar}")
            campo_monto = wait.until(
                EC.presence_of_element_located((By.ID, "inputOriginCountry"))
            )
            campo_monto.clear()
            time.sleep(1)
            campo_monto.send_keys(monto_a_cotizar)
            
            print("    -> Esperando cálculo de tasa...")
            time.sleep(2)
            
            # 4. Extraer Valor de Destino
            xpath_valor_destino = "//input[@id='inputDestinyCountry']"
            
            wait.until(lambda driver: self._wait_for_destination_value(driver, xpath_valor_destino))
            
            elemento_destino = self.driver.find_element(By.XPATH, xpath_valor_destino)
            valor_recibido_str = elemento_destino.get_attribute("value")
            print(f"    -> Valor recibido capturado: {valor_recibido_str}")

            # 5. Limpieza y Cálculo
            try:
                valor_recibido_limpio = re.sub(r'[^\d\.]', '', valor_recibido_str.replace(',', ''))
                valor_recibido = float(valor_recibido_limpio)
                monto_enviado = float(monto_a_cotizar.replace(',', ''))

                if valor_recibido == 0:
                    print(f"  ⚠️ ADVERTENCIA: El valor recibido es 0")
                    return 0.0, monto_a_cotizar

                tasa_directa = valor_recibido / monto_enviado
                print(f"    ✅ Tasa calculada: {tasa_directa:.6f}")
                return tasa_directa, monto_a_cotizar

            except (ValueError, ZeroDivisionError) as e:
                print(f"  🚨 ERROR al calcular: {e}")
                return 0.0, monto_a_cotizar
                
        except TimeoutException:
            print(f"  ❌ TIMEOUT en {self.nombre} para {ruta}")
            return 0.0, monto_a_cotizar
        except NoSuchElementException:
            print(f"  ❌ ELEMENTO NO ENCONTRADO en {self.nombre} para {ruta}")
            return 0.0, monto_a_cotizar
        except Exception as e:
            print(f"  ❌ ERROR inesperado en {self.nombre} para {ruta}: {e}")
            import traceback
            traceback.print_exc()
            return 0.0, monto_a_cotizar