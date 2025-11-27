from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import re
import time
from data_config import URLS_COMPETIDORES

class PaysendScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "Paysend", URLS_COMPETIDORES.get("Paysend", "https://paysend.com/"))
        
        self.url_map = {
            "CLP": "https://paysend.com/es-cl",
            "COP": "https://paysend.com/es-co",
            "EUR": "https://paysend.com/es-es",
            "USD": "https://paysend.com/en-us",
            "GBP": "https://paysend.com/en-gb",
        }
        
        # IDs de países (minúsculas)
        self.country_ids = {
            "COP": "co", "USD": "us", "ARS": "ar", "PEN": "pe",
            "EUR": "es", "VES": "ve", "MXN": "mx", "BRL": "br", "CLP": "cl"
        }
        
        # Textos para validación de sub-menú de moneda
        self.currency_names = {
            "COP": "Colombian Peso",
            "PEN": "Peruvian sol", 
            "ARS": "Peso",
            "USD": "US Dollar"
        }

    def _clean_amount(self, value_str):
        if not value_str: return 0.0
        clean = re.sub(r'[^\d\.,]', '', str(value_str))
        if not clean: return 0.0

        # Lógica de decimales
        if ',' in clean and '.' in clean:
            if clean.rindex(',') > clean.rindex('.'): 
                clean = clean.replace('.', '').replace(',', '.')
            else:
                clean = clean.replace(',', '')
        elif ',' in clean:
            if len(clean.split(',')[-1]) == 2: 
                clean = clean.replace(',', '.')
            else:
                clean = clean.replace(',', '')
        
        try: return float(clean)
        except: return 0.0

    def _ingresar_monto_humano(self, monto):
        """Escribe el monto de forma humana para evitar errores de máscara"""
        print(f"    -> Escribiendo monto: {monto}")
        try:
            # Usamos el ID confirmado __ifc__from_amount
            wait = WebDriverWait(self.driver, 10)
            input_el = wait.until(EC.visibility_of_element_located((By.ID, "__ifc__from_amount")))
            
            self.driver.execute_script("arguments[0].click();", input_el)
            time.sleep(0.2)
            
            # Borrado manual (Ctrl+A -> Backspace)
            input_el.send_keys(Keys.CONTROL + "a")
            time.sleep(0.1)
            input_el.send_keys(Keys.BACK_SPACE)
            time.sleep(0.2)
            
            # Escribir
            monto_entero = str(int(float(monto))) # Paysend prefiere enteros al escribir
            input_el.send_keys(monto_entero)
            time.sleep(1)
            
            # Clic fuera para que calcule
            self.driver.find_element(By.TAG_NAME, "body").click()
            return True
        except Exception as e:
            print(f"      ⚠️ Error escribiendo monto: {e}")
            return False

    def _seleccionar_destino_robusto(self, moneda_codigo):
        """
        Selecciona el país destino usando IDs y fuerza bruta JS.
        """
        pais_iso = self.country_ids.get(moneda_codigo)
        if not pais_iso: return False
        
        target_id = f"to-{pais_iso}"
        print(f"    -> Buscando destino (ID: {target_id})...")

        try:
            wait = WebDriverWait(self.driver, 10)
            
            # 1. Abrir el menú
            # Usamos un selector genérico para el botón si el testid falla
            trigger = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='amount-label-to']")))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", trigger)
            time.sleep(0.5)
            trigger.click()
            time.sleep(1.5) # Esperar animación de lista

            # 2. Buscar el elemento del país en la lista
            # Buscamos por ID exacto
            try:
                # Buscamos TODOS los elementos con ese ID (a veces hay duplicados ocultos)
                opciones = self.driver.find_elements(By.ID, target_id)
                target_opcion = None
                
                for op in opciones:
                    if op.is_displayed():
                        target_opcion = op
                        break
                
                if not target_opcion and opciones:
                    # Si ninguno dice displayed, probamos el primero igual
                    print("      ⚠️ Elemento encontrado pero reporta no visible. Intentando forzar...")
                    target_opcion = opciones[0]

                if target_opcion:
                    # Scroll y Click JS (Infalible)
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_opcion)
                    time.sleep(0.5)
                    self.driver.execute_script("arguments[0].click();", target_opcion)
                    print(f"      ✅ Clic JS enviado a #{target_id}")
                    time.sleep(2) # Esperar cierre de menú
                else:
                    print(f"      ❌ No se encontró el elemento #{target_id} en el DOM.")
                    return False

            except Exception as e:
                print(f"      ⚠️ Error buscando opción país: {e}")
                return False

            # 3. SUB-MENÚ DE MONEDA (Si aplica)
            # Si el país tiene varias monedas, aparece otro menú o lista
            try:
                codigo_moneda = moneda_codigo
                if codigo_moneda == "US":
                    codigo_moneda = "USD"

                # Esperamos a ver si aparece algún link con un span que tenga EXACTAMENTE ese código
                wait = WebDriverWait(self.driver, 5)

                xpath_opcion_moneda = (
                    f"//a[.//span[normalize-space(text())='{codigo_moneda}']]"
                )

                opcion_moneda = wait.until(
                    EC.element_to_be_clickable((By.XPATH, xpath_opcion_moneda))
                )

                # Scroll y click en el <a> completo
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    opcion_moneda,
                )
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].click();", opcion_moneda)
                print(f"      -> Seleccionando sub-moneda por código: {codigo_moneda}")
                time.sleep(1)

            except Exception as e:
                # Si no hay submenú o no aparece la moneda, seguimos sin romper el flujo
                print(f"      ⚠️ No se seleccionó sub-moneda (puede no ser necesaria): {e}")

            # Cerrar menú si sigue abierto (clic en body)
            try: self.driver.find_element(By.TAG_NAME, "body").click()
            except: pass
            
            return True

        except Exception as e:
            print(f"      ⚠️ Error crítico seleccionando destino: {e}")
            return False

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        # Ajustes
        if moneda_destino == "US": moneda_destino = "USD"
        if moneda_origen == "US": moneda_origen = "USD"
        if moneda_origen == "USD": moneda_origen = "USA" # Paysend a veces usa USA en URL

        # Obtener URL correcta
        url_key = moneda_origen if moneda_origen in self.url_map else "USD"
        url = self.url_map.get(url_key, "https://paysend.com/")
        
        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        try:
            self.driver.get(url)
            time.sleep(4) # Carga inicial

            # Cookies (cerrar rápido)
            try: self.driver.find_element(By.ID, "onetrust-accept-btn-handler").click()
            except: pass

            # 1. SELECCIONAR DESTINO
            self._seleccionar_destino_robusto(moneda_destino)

            # 2. INGRESAR MONTO
            self._ingresar_monto_humano(monto_a_cotizar)

            print("    -> Esperando cálculo...")
            time.sleep(5)

            # 3. EXTRAER TASA
            tasa_final = 0.0
            
            # A) Texto "Today's rate" / "Cambio de hoy"
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                # Busca "1.00 [ORIGEN] = [NUMERO]"
                # Paysend muestra ej: "1.00 USD = 950.50 CLP"
                patron = r'=\s*([\d\.,]+)\s*' + (moneda_destino if moneda_destino != "US" else "USD")
                match = re.search(patron, body_text)
                
                if match:
                    val_str = match.group(1)
                    # Ajuste para USD/EUR (punto decimal) vs Latam (coma decimal)
                    if "USD" in moneda_origen or "EUR" in moneda_origen or "GBP" in moneda_origen:
                         val_str = val_str.replace(',', '') # 1,234.56 -> 1234.56
                    else:
                         val_str = val_str.replace('.', '').replace(',', '.') # 1.234,56 -> 1234.56
                    
                    tasa_final = float(val_str)
                    print(f"    ✅ Tasa encontrada (Texto): {tasa_final}")
            except: pass

            # B) Cálculo por Inputs (Plan B)
            if tasa_final == 0:
                try:
                    val_in = self.driver.find_element(By.ID, "__ifc__from_amount").get_attribute("value")
                    val_out = self.driver.find_element(By.ID, "__ifc__to_amount").get_attribute("value")
                    
                    n_in = self._clean_amount(val_in)
                    n_out = self._clean_amount(val_out)
                    
                    # Filtro de coherencia (evitar trillones)
                    if n_in > 0 and n_out > 0 and n_in < 100000000:
                        tasa_final = n_out / n_in
                        print(f"    🧮 Tasa calculada ({n_out} / {n_in}): {tasa_final:.6f}")
                    else:
                        print(f"    ⚠️ Inputs incoherentes: {n_in} -> {n_out}")

                except Exception as e:
                    print(f"    ⚠️ Falló cálculo inputs: {e}")

            return tasa_final, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en Paysend: {e}")
            return 0.0, monto_a_cotizar