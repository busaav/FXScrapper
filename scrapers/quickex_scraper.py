from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
from data_config import URLS_COMPETIDORES

class QuickexScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "Quickex", URLS_COMPETIDORES.get("Quickex", "https://www.quickex.net/"))

    def _seleccionar_ddslick(self, container_id, moneda_texto):
        """
        Maneja selectores tipo ddSlick (div id="currency-1" class="dd-container")
        """
        print(f"    -> Buscando '{moneda_texto}' en {container_id}...")
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # 1. Encontrar el contenedor principal
            container = self.driver.find_element(By.ID, container_id)
            
            # 2. Abrir el menú haciendo clic en .dd-select
            # Usamos JS para evitar errores de "elemento interceptado"
            select_trigger = container.find_element(By.CLASS_NAME, "dd-select")
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", container)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", select_trigger)
            time.sleep(1) # Esperar a que la lista se despliegue visualmente
            
            # 3. Buscar la opción específica
            # En tus capturas, el texto está dentro de <label class="dd-option-text">CLP</label>
            # Pero el elemento clicable es el padre <a class="dd-option">
            
            xpath_target = f".//*[@id='{container_id}']//label[contains(text(), '{moneda_texto}')]/ancestor::a[contains(@class, 'dd-option')]"
            
            # Verificar si existe
            opcion = self.driver.find_element(By.XPATH, xpath_target)
            
            # 4. Hacer clic en la opción
            self.driver.execute_script("arguments[0].click();", opcion)
            print(f"      ✅ Seleccionado: {moneda_texto}")
            
            # 5. Cerrar forzosamente cualquier menú abierto haciendo clic en el body
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(1)
            return True

        except Exception as e:
            print(f"      ⚠️ Error seleccionando {moneda_texto}: {e}")
            # Intentar cerrar el menú por si acaso quedó abierto
            try: self.driver.find_element(By.TAG_NAME, "body").click()
            except: pass
            return False

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        # --- AJUSTES DE NOMBRES SEGÚN LA WEB ---
        # En Quickex, a veces aparece "USA_USD" o "USD".
        # Según tus capturas, para destino se ve "USD" con bandera de Ecuador y "USA_USD" con bandera de USA.
        # Generalmente "USD" funciona para el genérico.
        
        if moneda_origen == "USD": moneda_origen = "USA_USD" 
        if moneda_destino == "US": moneda_destino = "USD"
        
        # Caso especial: Si piden CLP -> USD, asegurarnos de buscar "USD" (o USA_USD si falla)
        # ---------------------------------------

        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        try:
            self.driver.get(self.url_base)
            self.driver.refresh()
            time.sleep(5) # Espera inicial importante
            
            # 1. SELECCIONAR ORIGEN (ID: currency-1)
            if not self._seleccionar_ddslick("currency-1", moneda_origen):
                print("    ⛔ Falló selección de origen. Saltando ruta.")
                return 0.0, monto_a_cotizar

            # 2. SELECCIONAR DESTINO (ID: currency-2)
            if not self._seleccionar_ddslick("currency-2", moneda_destino):
                print("    ⛔ Falló selección de destino. Saltando ruta.")
                return 0.0, monto_a_cotizar
            
            # 3. INGRESAR MONTO
            try:
                input_monto = self.driver.find_element(By.ID, "amount")
                self.driver.execute_script("arguments[0].value = '';", input_monto)
                input_monto.send_keys(monto_a_cotizar)
                
                # Disparar eventos para que la web sepa que cambió
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", input_monto)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", input_monto)
                
                # Clic fuera para activar cálculo
                self.driver.find_element(By.TAG_NAME, "body").click()
            except Exception as e:
                print(f"    ⚠️ Error ingresando monto: {e}")

            print("    -> Esperando cálculo...")
            time.sleep(5) 
            
            # 4. OBTENER RESULTADO (TASA)
            tasa_final = 0.0
            
            # Estrategia A: Texto "Tasa actual"
            try:
                elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Tasa actual')]")
                for el in elements:
                    if el.is_displayed():
                        text = el.text
                        match = re.search(r'([\d\.]+)', text.replace('Tasa actual', '').strip())
                        if match:
                            tasa_final = float(match.group(1))
                            print(f"    ✅ Tasa leída (Texto): {tasa_final}")
                            break
            except: pass
            
            # Estrategia B: Cálculo matemático (Inputs)
            if tasa_final == 0:
                try:
                    input_origen = self.driver.find_element(By.ID, "amount")
                    input_destino = self.driver.find_element(By.ID, "amount-to")
                    
                    val_orig = float(re.sub(r'[^\d\.]', '', input_origen.get_attribute("value")))
                    val_dest = float(re.sub(r'[^\d\.]', '', input_destino.get_attribute("value")))
                    
                    if val_orig > 0 and val_dest > 0:
                        tasa_final = val_dest / val_orig
                        print(f"    🧮 Tasa calculada ({val_dest}/{val_orig}): {tasa_final:.6f}")
                except: pass

            if tasa_final > 0:
                return tasa_final, monto_a_cotizar

            return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en Quickex: {e}")
            return 0.0, monto_a_cotizar