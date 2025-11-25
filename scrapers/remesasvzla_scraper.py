from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import re
import time
from data_config import URLS_COMPETIDORES

class RemesasVzlaScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "Remesas Vzla", URLS_COMPETIDORES.get("Remesas Vzla", "https://remesasvzla.com/"))
        
        # Mapeo para buscar en el Select2 (usamos nombres de países o monedas comunes)
        self.search_map = {
            "CLP": "CLP",
            "VES": "VES",
        }

    def _seleccionar_select2(self, select_id, termino_busqueda):
        """
        Maneja la interacción específica con librerías Select2.
        1. Clic en el contenedor del select2.
        2. Esperar a que aparezca el input de búsqueda.
        3. Escribir y dar Enter.
        """
        print(f"    -> Seleccionando '{termino_busqueda}' en #{select_id}...")
        try:
            wait = WebDriverWait(self.driver, 10)
            
            # 1. Encontrar el contenedor visual del Select2 (es el hermano inmediato del select oculto)
            # XPath: Busca el select por ID, luego su hermano span con clase 'select2'
            xpath_trigger = f"//select[@id='{select_id}']/following-sibling::span[contains(@class, 'select2-container')]"
            
            trigger = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_trigger)))
            trigger.click()
            
            # 2. Esperar y buscar el campo de búsqueda (aparece en el DOM al abrir el dropdown)
            # La clase estándar de Select2 para el input de búsqueda es 'select2-search__field'
            search_box = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "select2-search__field")))
            
            # 3. Escribir y seleccionar
            search_box.clear()
            search_box.send_keys(termino_busqueda)
            time.sleep(0.5) # Esperar filtrado
            search_box.send_keys(Keys.ENTER)
            time.sleep(0.5)
            
            print(f"      ✅ Selección realizada.")
            return True

        except Exception as e:
            print(f"      ⚠️ Error Select2 ({select_id}): {e}")
            # Intentar cerrar el dropdown si quedó abierto (click en body)
            try: self.driver.find_element(By.TAG_NAME, "body").click()
            except: pass
            return False

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        # Convertir códigos a términos de búsqueda (ej: CLP -> Chile)
        term_origen = self.search_map.get(moneda_origen, moneda_origen)
        term_destino = self.search_map.get(moneda_destino, moneda_destino)
        
        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        try:
            self.driver.get(self.url_base)
            time.sleep(4) # Espera de carga inicial

            # 1. SELECCIONAR ORIGEN (ID nativo: fromCcy)
            if not self._seleccionar_select2("fromCcy", term_origen):
                print("    ⛔ Falló selección de origen.")
                return 0.0, monto_a_cotizar

            # 2. SELECCIONAR DESTINO (ID nativo: toCcy)
            if not self._seleccionar_select2("toCcy", term_destino):
                print("    ⛔ Falló selección de destino.")
                # A veces el destino se pone automático, intentamos continuar
            
            # 3. INGRESAR MONTO (ID: fromAmount)
            try:
                input_envio = self.driver.find_element(By.ID, "fromAmount")
                input_envio.clear()
                input_envio.send_keys(monto_a_cotizar)
                # Disparar eventos para forzar recálculo
                input_envio.send_keys(Keys.TAB) 
                time.sleep(0.5)
            except Exception as e:
                print(f"    ⚠️ Error ingresando monto: {e}")

            print("    -> Esperando cálculo...")
            time.sleep(3) 

            # 4. EXTRAER RESULTADO (ID: toAmount)
            tasa_final = 0.0
            try:
                # El resultado está en un input readonly con id='toAmount'
                input_recibo = self.driver.find_element(By.ID, "toAmount")
                val_recibo = input_recibo.get_attribute("value") # Ej: "1.234,56"
                
                if val_recibo:
                    # Limpieza de formato (quitar puntos de miles, cambiar coma decimal a punto)
                    # Asumimos formato latino (1.000,00) común en webs de Vzla/Chile
                    clean_val = val_recibo.replace('.', '').replace(',', '.')
                    
                    monto_recibido = float(re.sub(r'[^\d\.]', '', clean_val))
                    monto_enviado = float(monto_a_cotizar)

                    if monto_recibido > 0:
                        tasa_final = monto_recibido / monto_enviado
                        print(f"    ✅ Tasa calculada ({monto_recibido} / {monto_enviado}): {tasa_final:.6f}")

            except Exception as e:
                print(f"    ⚠️ Error leyendo resultado: {e}")

            if tasa_final > 0:
                return tasa_final, monto_a_cotizar
            
            return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en Remesas Vzla: {e}")
            return 0.0, monto_a_cotizar