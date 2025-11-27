from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import re
import time
from data_config import URLS_COMPETIDORES

class MiPapayaScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "Mi Papaya", URLS_COMPETIDORES.get("Mi Papaya", "https://mipapaya.app/"))
        
        # Mapeo Moneda -> País (Tal como aparecen en el menú)
        self.country_map = {
            "CLP": "Chile",
            "VES": "Venezuela",
            "COP": "Colombia",
            "PEN": "Perú",
            "BRL": "Brasil",
            "USD": "Estados Unidos",
            "MXN": "México",
            "CRC": "Costa Rica"
        }

    def _seleccionar_pais(self, tipo, moneda_codigo):
        """
        Selecciona el país en los dropdowns de origen o destino.
        tipo: 0 para Origen, 1 para Destino (basado en el orden visual en la página)
        """
        pais_nombre = self.country_map.get(moneda_codigo, moneda_codigo)
        print(f"    -> Seleccionando {pais_nombre} en selector #{tipo+1}...")
        
        try:
            wait = WebDriverWait(self.driver, 15)
            
            # 1. Identificar los dropdowns (Selectores de país)
            # En MiPapaya suelen ser divs con clase 'mat-select' o similar, o botones.
            # Buscamos por la estructura visual: Hay dos selectores principales de banderas/países.
            
            # Estrategia: Buscar elementos que parezcan selectores (flecha hacia abajo o clase 'select')
            # Ojo: MiPapaya usa Angular/Material a veces. Buscamos el contenedor genérico.
            
            # Intento A: Buscar por elementos 'select' ocultos o simulados
            potential_dropdowns = self.driver.find_elements(By.CSS_SELECTOR, ".mat-select, .ng-select, [role='combobox'], .dropdown-toggle")
            
            # Si no hay selectores claros, buscamos por los contenedores de las banderas/nombres
            if not potential_dropdowns:
                 potential_dropdowns = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'select') or contains(@class, 'input-wrapper')]//div[contains(@class, 'value')]")

            if len(potential_dropdowns) >= 2:
                target = potential_dropdowns[tipo]
            else:
                # Fallback: Buscar por texto cercano
                if tipo == 0: # Origen
                    # A veces el origen ya muestra "Estados Unidos" o el país actual
                    target = self.driver.find_element(By.XPATH, "(//div[contains(@class, 'select')])[1]")
                else: # Destino
                    # El destino suele decir "País de destino"
                    target = self.driver.find_element(By.XPATH, "//*[contains(text(), 'País de destino')]/ancestor::div[contains(@class, 'mat-form-field')]")

            # 2. Clic para abrir
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
            time.sleep(0.5)
            
            # Intentar click normal y JS
            try: target.click()
            except: self.driver.execute_script("arguments[0].click();", target)
            
            time.sleep(1) # Esperar animación de lista
            
            # 3. Buscar opción en la lista desplegada
            # En Angular Material, las opciones suelen estar en un 'div.cdk-overlay-container' al final del body
            xpath_option = f"//span[contains(text(), '{pais_nombre}')] | //mat-option//span[contains(., '{pais_nombre}')] | //li[contains(., '{pais_nombre}')]"
            
            opcion = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_option)))
            opcion.click()
            
            # Cerrar por si acaso (clic en body)
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(1)
            print(f"      ✅ Selección realizada: {pais_nombre}")
            return True

        except Exception as e:
            print(f"      ⚠️ Error seleccionando {pais_nombre}: {e}")
            # Intentar cerrar cualquier menú abierto
            try: self.driver.find_element(By.TAG_NAME, "body").click()
            except: pass
            return False

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        try:
            self.driver.get(self.url_base)
            time.sleep(5) # Espera carga

            # 1. Seleccionar Origen (Primer selector)
            self._seleccionar_pais(0, moneda_origen)
            
            # 2. Seleccionar Destino (Segundo selector)
            self._seleccionar_pais(1, moneda_destino)

            # 3. Ingresar Monto
            try:
                # Buscar input numérico visible
                inputs = self.driver.find_elements(By.XPATH, "//input[@type='number' or @type='tel']")
                # El primer input habilitado suele ser el de envío
                input_envio = None
                for i in inputs:
                    if i.is_displayed() and i.is_enabled():
                        input_envio = i
                        break
                
                if input_envio:
                    input_envio.clear()
                    input_envio.send_keys(monto_a_cotizar)
                    # Forzar evento de actualización
                    input_envio.send_keys(Keys.TAB)
                    self.driver.find_element(By.TAG_NAME, "body").click()
                else:
                    print("    ⚠️ No se encontró input de monto.")
            except Exception as e:
                print(f"    ⚠️ Error ingresando monto: {e}")

            print("    -> Esperando cálculo...")
            time.sleep(5)

            # 4. Extraer Tasa ("Tasa Papaya 1 USD = 276.14 VES")
            tasa_final = 0.0
            try:
                # Buscar el texto específico "Tasa Papaya"
                elementos = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Tasa Papaya') or contains(text(), 'Exchange rate')]")
                
                for el in elementos:
                    texto = el.text
                    # Regex para buscar "1 MONEDA = VALOR" o "Tasa ... VALOR"
                    # Ej: "Tasa Papaya 1 USD = 276.14 VES"
                    # Buscamos el número que está después del "="
                    match = re.search(r'=\s*([\d\.,]+)', texto)
                    
                    if match:
                        val_str = match.group(1).replace(',', '.')
                        # Si tiene multiples puntos, limpiar
                        if val_str.count('.') > 1: val_str = val_str.replace('.', '', val_str.count('.')-1)
                        
                        tasa_final = float(val_str)
                        print(f"    ✅ Tasa encontrada en texto: {tasa_final}")
                        return tasa_final, monto_a_cotizar

                # Fallback: Buscar por clase si el texto varía
                # A veces el valor está en un span separado
                if tasa_final == 0:
                     # Intento de cálculo matemático por inputs
                     inputs = self.driver.find_elements(By.XPATH, "//input[@type='number' or @type='tel']")
                     visibles = [x for x in inputs if x.is_displayed()]
                     if len(visibles) >= 2:
                         val_in = float(visibles[0].get_attribute("value"))
                         val_out = float(visibles[1].get_attribute("value"))
                         if val_in > 0:
                             tasa_final = val_out / val_in
                             print(f"    🧮 Tasa calculada: {tasa_final:.6f}")
                             return tasa_final, monto_a_cotizar

            except Exception as e:
                print(f"    ⚠️ Error extrayendo tasa: {e}")

            return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en Mi Papaya: {e}")
            return 0.0, monto_a_cotizar