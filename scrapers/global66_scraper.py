from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import time
from data_config import URLS_COMPETIDORES

class Global66Scraper(BaseScraper):
    # La URL se obtiene del diccionario global, pero se asigna aquí
    def __init__(self, driver):
        super().__init__(driver, "Global66", URLS_COMPETIDORES["Global66"])
    
    def _handle_popup(self, wait):
        """Maneja múltiples tipos de pop-ups que pueden aparecer"""
        print("    -> Buscando pop-ups para cerrar...")
        
        try:
            # Esperar a que el modal exista en el DOM
            modal_wait = WebDriverWait(self.driver, 10)
            
            modal = modal_wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.vfm__container[role='dialog']"))
            )
            
            # 🔥 VERIFICACIÓN CRÍTICA: Comprobar si tiene display: none
            display_style = modal.value_of_css_property("display")
            print(f"    -> Modal encontrado. Display: {display_style}")
            
            if display_style == "none":
                print("    -> Modal oculto (display: none), no hay pop-up activo. Continuando.")
                return False
            
            # Si llegamos aquí, el modal está visible
            print(f"    -> ✅ Pop-up visible detectado!")
            
            # Esperar a que la animación termine
            time.sleep(3)
            
            # Buscar el botón de cerrar
            try:
                close_button = modal.find_element(By.CSS_SELECTOR, "button.close-button")
                
                # Verificar que el botón también sea visible
                if close_button.is_displayed():
                    print(f"    -> Botón de cerrar visible, haciendo clic...")
                    self.driver.execute_script("arguments[0].click();", close_button)
                    time.sleep(1)
                    
                    # Verificar que se cerró (ahora debe tener display: none)
                    display_after = modal.value_of_css_property("display")
                    if display_after == "none":
                        print("    -> ✅ Pop-up cerrado exitosamente!")
                        return True
                    else:
                        print(f"    -> ⚠️ Modal aún visible (display: {display_after})")
                else:
                    print("    -> ⚠️ Botón encontrado pero no visible")
                    
            except NoSuchElementException:
                print("    -> ⚠️ Botón close-button no encontrado")
            
            # Plan B: Buscar todos los botones visibles en el modal
            print("    -> Plan B: Buscando botones visibles...")
            buttons = modal.find_elements(By.TAG_NAME, "button")
            visible_buttons = [btn for btn in buttons if btn.is_displayed()]
            print(f"    -> Encontrados {len(visible_buttons)} botones visibles")
            
            for i, btn in enumerate(visible_buttons):
                print(f"    -> Intentando botón #{i+1}")
                self.driver.execute_script("arguments[0].click();", btn)
                time.sleep(1)
                
                display_after = modal.value_of_css_property("display")
                if display_after == "none":
                    print(f"    -> ✅ Pop-up cerrado con botón #{i+1}!")
                    return True
            
            # Plan C: ESC
            print("    -> Plan C: Intentando ESC...")
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
            
            display_after = modal.value_of_css_property("display")
            if display_after == "none":
                print("    -> ✅ Pop-up cerrado con ESC!")
                return True
            
            print("    -> ❌ No se pudo cerrar el pop-up")
            return False
                
        except TimeoutException:
            print("    -> No se encontró el modal en el DOM. Continuando.")
            return False
        except Exception as e:
            print(f"    -> ❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        return False


    def _wait_for_destination_value(self, driver, xpath):
        """Función auxiliar para esperar que el valor de destino se llene"""
        try:
            element = driver.find_element(By.XPATH, xpath)
            value = element.get_attribute("value")
            if not value:
                return False
            # Limpiar y verificar que sea mayor a 0
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

        self._handle_popup(wait)

        print("    -> Esperando carga completa de la página...")
        time.sleep(3)  # Dar tiempo a que el pop-up aparezca
    
        self._handle_popup(wait)
        time.sleep(1)  # Pausa adicional después de cerrar


        try:
            # 1. Seleccionar País/Moneda de Origen y Destino
            # Global66: Usamos selectores CSS para los contenedores y XPATH para la moneda
            
           # --- Moneda de Origen ---
            selector_origen_multiselect = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".multiselect.country-vmultiselect:not(.destiny)"))
            )
            selector_origen_multiselect.click()
            
            # Hacer clic en la opción de la lista que contiene el código de la moneda
            xpath_moneda_origen = f"//span[contains(text(), '{moneda_origen}')]"
            wait.until(EC.element_to_be_clickable((By.XPATH, xpath_moneda_origen))).click()
            time.sleep(0.5)  # Pequeña pausa para que se actualice la UI
            
            # --- Moneda de Destino ---
            selector_destino_multiselect = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".multiselect.country-vmultiselect.destiny"))
            )
            selector_destino_multiselect.click()
            
            # Hacer clic en la opción de destino
            xpath_moneda_destino = f"//span[contains(text(), '{moneda_destino}')]"
            wait.until(EC.element_to_be_clickable((By.XPATH, xpath_moneda_destino))).click()
            time.sleep(0.5)  # Pequeña pausa para que se actualice la UI
            
            # 2. Ingresar el Monto
            campo_monto = wait.until(
                EC.presence_of_element_located((By.ID, "inputOriginCountry")) 
            )
            campo_monto.clear()
            time.sleep(0.3)  # Pausa después del clear
            campo_monto.send_keys(monto_a_cotizar) 

            print("    -> Esperando cálculo de tasa...")
            time.sleep(2)  # Dar tiempo para que la API calcule
            
            # --- 3. EXTRAER VALOR DE DESTINO PARA CALCULAR LA TASA ---

            # XPATH para el input que dice "Tu contacto recibe" (inputDestinyCountry)
            xpath_valor_destino = "//input[@id='inputDestinyCountry']" 

            # Esperamos a que el valor de destino se llene (indicando que el cálculo terminó)
            wait.until(lambda driver: self._wait_for_destination_value(driver, xpath_valor_destino))
            
            elemento_destino = self.driver.find_element(By.XPATH, xpath_valor_destino)
            valor_recibido_str = elemento_destino.get_attribute("value")
            print(f"    -> Valor recibido capturado: {valor_recibido_str}")

            # 4. Limpieza y Cálculo Implícito
            try:
                # Limpiamos el valor (quitamos comas, espacios y símbolos de moneda, solo mantenemos números y puntos)
                valor_recibido_limpio = re.sub(r'[^\d\.]', '', valor_recibido_str.replace('.', ''))
                
                valor_recibido = float(valor_recibido_limpio)
                monto_enviado = float(monto_a_cotizar.replace(',', ''))

                if valor_recibido == 0:
                    print(f"  ⚠️ ADVERTENCIA: El valor recibido es 0")
                    return 0.0, monto_a_cotizar
                # La tasa directa (1 unidad de origen = X unidades de destino) no es lo que necesitamos.
                # Lo que queremos es la tasa que se usa en el mercado: 1 unidad de DESTINO (VES) = X unidades de ORIGEN (COP/CLP)
                
                # Tasa Directa (1 USD/CLP/COP = X VES) = Valor Recibido / Monto Enviado
                tasa_directa = valor_recibido / monto_enviado
                print(f"    ✅ Tasa calculada: {tasa_directa:.6f}")

                #La cargaremos como Tasa Directa en el reporte
                # para que el cálculo en el main (1/TasaDirecta) te dé el valor de mercado.
                return tasa_directa, monto_a_cotizar 

            except Exception as e:
                print(f"  🚨 ERROR: Falla al limpiar o calcular el valor: {e}")
                return 0.0, monto_a_cotizar
        except (TimeoutException, NoSuchElementException) as e:
            print(f"  ❌ FALLO en {self.nombre} para {ruta}: Elemento no encontrado o tiempo agotado. {type(e).__name__}")
            return 0.0, monto_a_cotizar
        except Exception as e:
            print(f"  ❌ FALLO inesperado en {self.nombre} para {ruta}: {e}")
            import traceback
            traceback.print_exc()
            return 0.0, monto_a_cotizar