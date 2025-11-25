from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import re
import time
from data_config import URLS_COMPETIDORES

class TuCambioScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "TuCambio CL", "https://www.tucambio.app/en")
        self.country_map = {
            "CLP": "Chile",
            "VES": "Venezuela",
            "ARS": "Argentina",
            "COP": "Colombia",
            "PEN": "Perú",
            "USD": "USA", 
            "US": "USA",
            "MXN": "México",
            "BOB": "Bolivia"
        }

    def _get_selected_country(self, section_keyword):
        """Lee qué país/moneda está seleccionado actualmente en el botón"""
        try:
            xpath_label = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{section_keyword}')]"
            labels = self.driver.find_elements(By.XPATH, xpath_label)
            target_label = None
            for l in labels:
                if l.is_displayed():
                    target_label = l
                    break
            
            if not target_label: return None
            
            label_y = target_label.location['y']
            all_btns = self.driver.find_elements(By.XPATH, "//button[.//img]")
            
            target_btn = None
            min_dist = 9999
            
            for btn in all_btns:
                if not btn.is_displayed(): continue
                dist = btn.location['y'] - label_y
                if 0 < dist < 250 and dist < min_dist:
                    min_dist = dist
                    target_btn = btn
            
            if target_btn:
                return target_btn.text.strip()
        except:
            pass
        return None

    def _seleccionar_moneda_smart(self, section_keyword, moneda_codigo):
        pais_nombre = self.country_map.get(moneda_codigo, moneda_codigo)
        print(f"    -> Configurando '{section_keyword}' a '{pais_nombre}' (o '{moneda_codigo}')...")

        def es_correcto(texto_boton):
            if not texto_boton: return False
            txt = texto_boton.lower()
            return (pais_nombre.lower() in txt) or (moneda_codigo.lower() in txt)

        # 1. Verificar si ya está seleccionado
        actual = self._get_selected_country(section_keyword)
        if es_correcto(actual):
            print(f"      ✅ Ya estaba seleccionado correctamente: {actual}")
            return True

        try:
            wait = WebDriverWait(self.driver, 20)
            
            xpath_label = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{section_keyword}')]"
            # Usamos wait para asegurar que el elemento base existe
            target_label = wait.until(EC.visibility_of_element_located((By.XPATH, xpath_label)))
            
            label_y = target_label.location['y']
            all_btns = self.driver.find_elements(By.XPATH, "//button[.//img]")
            
            target_btn = None
            min_dist = 9999
            for btn in all_btns:
                if not btn.is_displayed(): continue
                dist = btn.location['y'] - label_y
                if 0 < dist < 250 and dist < min_dist:
                    min_dist = dist
                    target_btn = btn
            
            if not target_btn: 
                print("      ⚠️ No se encontró botón dropdown.")
                return False

            # 2. Abrir Menú
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", target_btn)
            time.sleep(1) 

            # 3. Buscar Opción
            xpath_opcion = f"//div[contains(@role, 'menu')]//button[contains(., '{pais_nombre}')] | //li[contains(., '{pais_nombre}')] | //div[contains(text(), '{pais_nombre}')]"
            
            try:
                opciones = self.driver.find_elements(By.XPATH, xpath_opcion)
                visible_opt = next((o for o in opciones if o.is_displayed()), None)
                
                if visible_opt:
                    visible_opt.click()
                else:
                    xpath_code = f"//div[contains(@role, 'menu')]//button[contains(., '{moneda_codigo}')]"
                    opcion_code = self.driver.find_element(By.XPATH, xpath_code)
                    self.driver.execute_script("arguments[0].click();", opcion_code)

            except Exception as e:
                print(f"      ⚠️ Error click opción: {e}")
                self.driver.find_element(By.TAG_NAME, "body").click()
                return False

            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(1.5)
            
            # 4. Verificación
            nuevo_actual = self._get_selected_country(section_keyword)
            if es_correcto(nuevo_actual):
                print(f"      ✅ Cambio exitoso. Ahora muestra: {nuevo_actual}")
                return True
            else:
                print(f"      ⚠️ Advertencia visual: Dice '{nuevo_actual}' (Esperado: {pais_nombre})")
                return True

        except Exception as e:
            print(f"      ⚠️ Excepción selección: {e}")
            return False

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        if moneda_destino == "USD": moneda_destino = "US"
        
        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        try:
            self.driver.get(self.url_base)
            # ELIMINADO: self.driver.refresh() -> Causaba el timeout "aborted by navigation"
            
            # Espera explicita a que cargue la calculadora
            wait = WebDriverWait(self.driver, 20)
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "input")))
            except:
                print("    ⚠️ Timeout esperando carga inicial.")
                
            time.sleep(3) # Estabilización

            # 1. Selecciones
            if not self._seleccionar_moneda_smart("send", moneda_origen):
                print("    ⚠️ Problema seleccionando origen")
            
            time.sleep(1)

            if not self._seleccionar_moneda_smart("receive", moneda_destino):
                 print("    ⚠️ Problema seleccionando destino")

            # 2. Ingresar Monto
            try:
                xpath_input = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]/following::input[@type='text'][1]"
                input_monto = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_input)))
                
                self.driver.execute_script("arguments[0].value = '';", input_monto)
                input_monto.send_keys(monto_a_cotizar)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_monto)
                self.driver.find_element(By.TAG_NAME, "body").click()
            except Exception as e:
                print(f"    ⚠️ Error ingresando monto: {e}")

            print("    -> Esperando cálculo...")
            time.sleep(5)

            # 3. Extraer Tasa
            tasa_final = 0.0
            try:
                xpath_exacto = "//p[contains(., 'Exchange rate')]/following-sibling::p"
                elemento_tasa = self.driver.find_element(By.XPATH, xpath_exacto)
                match = re.search(r'([\d\.]+)', elemento_tasa.text.strip())
                if match:
                    tasa_final = float(match.group(1))
                    print(f"    ✅ Tasa leída del texto: {tasa_final}")
            except: pass

            # Estrategia B: Cálculo
            if tasa_final == 0:
                try:
                    xpath_recibo = "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'receive')]/following::input[@type='text'][1]"
                    input_recibo = self.driver.find_element(By.XPATH, xpath_recibo)
                    
                    val_orig = float(re.sub(r'[^\d\.]', '', str(input_monto.get_attribute("value")).replace(',','.')))
                    val_dest = float(re.sub(r'[^\d\.]', '', str(input_recibo.get_attribute("value")).replace(',','.')))
                    
                    if val_orig > 0:
                        tasa_final = val_dest / val_orig
                        print(f"    🧮 Tasa calculada: {tasa_final:.6f}")
                except: pass

            if tasa_final > 0:
                return tasa_final, monto_a_cotizar

            return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en TuCambio: {e}")
            return 0.0, monto_a_cotizar