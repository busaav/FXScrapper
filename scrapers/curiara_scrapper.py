from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
from data_config import URLS_COMPETIDORES

class CuriaraScraper(BaseScraper):
    def __init__(self, driver):
        super().__init__(driver, "Curiara", URLS_COMPETIDORES.get("Curiara", "https://curiara.com/"))
        
        self.rutas_urls = {
            "EURVES": "https://curiara.com/europa/",
            "COPVES": "https://curiara.com/enviar-dinero-colombia-venezuela/",
            "CLPVES": "https://curiara.com/enviar-dinero-chile-venezuela/",
        }

    def _cerrar_cookies(self):
        """Busca y cierra el banner de consentimiento de cookies."""
        print("    -> Buscando banner de cookies...")
        try:
            # Lista de posibles XPaths para el botón de Aceptar
            # Buscamos botones, divs o enlaces que digan "Aceptar", "Accept" o "Consentir"
            xpaths_cookies = [
                "//button[contains(., 'Aceptar')]",
                "//a[contains(., 'Aceptar')]",
                "//div[contains(., 'Aceptar') and @role='button']",
                "//span[contains(., 'Aceptar')]",
                "//*[contains(@class, 'cookie') or contains(@class, 'consent')]//button",
                "//button[contains(., 'Allow all')]"
            ]
            
            for xpath in xpaths_cookies:
                try:
                    elementos = self.driver.find_elements(By.XPATH, xpath)
                    for el in elementos:
                        if el.is_displayed():
                            # Verificación extra: que no sea un botón pequeño o irrelevante
                            if len(el.text) < 20: # "Aceptar" es corto
                                print(f"      🍪 Cerrando cookies (Click en: {el.text})...")
                                # Intentar click normal y luego JS
                                try:
                                    el.click()
                                except:
                                    self.driver.execute_script("arguments[0].click();", el)
                                time.sleep(1.5) # Esperar a que desaparezca el modal
                                return
                except: pass
        except Exception as e:
            print(f"      ⚠️ Error intentando cerrar cookies: {e}")

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        url = self.rutas_urls.get(ruta)
        if not url:
            print(f"    ❌ Ruta {ruta} no configurada.")
            return 0.0, "100"
            
        monto_a_cotizar = self._get_monto_a_cotizar(ruta[:3])
        
        try:
            self.driver.get(url)
            time.sleep(5) # Espera carga inicial

            # 1. INTENTO DE CIERRE DE COOKIES
            self._cerrar_cookies()

            # 2. EXTRACCIÓN DE TASA
            tasa_final = 0.0
            
            # Estrategia A: Buscar texto visible "Tasa: X"
            # Buscamos en todo el cuerpo visible para evitar problemas de selectores específicos
            try:
                # Obtenemos todo el texto de la página y buscamos el patrón
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                
                # Patrones comunes en Curiara: "Tasa: 366.01", "1 EUR = 366.01 VES"
                match = re.search(r'Tasa\s*:?\s*([\d\.,]+)', body_text, re.IGNORECASE)
                
                if match:
                    val_str = match.group(1)
                    # Normalización (si hay punto y coma, quitar punto de miles)
                    if ',' in val_str and '.' in val_str:
                        val_str = val_str.replace('.', '').replace(',', '.')
                    elif ',' in val_str:
                        val_str = val_str.replace(',', '.')
                    
                    tasa_final = float(val_str)
                    print(f"    ✅ Tasa encontrada en texto: {tasa_final}")

            except Exception as e:
                print(f"    ⚠️ Error analizando texto: {e}")

            # Estrategia B: Buscar elemento específico si el texto general falla
            if tasa_final == 0:
                try:
                    # XPath específico para el contenedor de tasas de Curiara
                    elementos = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Tasa')]/following-sibling::* | //*[contains(text(), 'Tasa')]/..")
                    for el in elementos:
                        if el.is_displayed():
                            txt = el.text
                            m = re.search(r'([\d\.,]+)', txt)
                            if m:
                                val = float(m.group(1).replace(',', '.'))
                                if val > 0:
                                    tasa_final = val
                                    print(f"    ✅ Tasa encontrada por elemento: {tasa_final}")
                                    break
                except: pass

            if tasa_final > 0:
                return tasa_final, monto_a_cotizar

            # Estrategia C: Cálculo por inputs (Plan de emergencia)
            print("    ⚠️ Tasa no detectada, intentando cálculo por inputs...")
            try:
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                # Filtrar inputs visibles y numéricos (o texto que parezca número)
                visibles = []
                for i in inputs:
                    if i.is_displayed() and i.get_attribute("type") in ["text", "tel", "number"]:
                        visibles.append(i)
                
                if len(visibles) >= 2:
                    # Asumimos 1ro: Envío, 2do: Recepción
                    input_envio = visibles[0]
                    input_envio.clear()
                    input_envio.send_keys(monto_a_cotizar)
                    input_envio.send_keys(Keys.TAB)
                    time.sleep(2)
                    
                    val_recibo = visibles[1].get_attribute("value")
                    if val_recibo:
                        clean_val = re.sub(r'[^\d\.,]', '', val_recibo).replace('.','').replace(',','.')
                        num_recibo = float(clean_val)
                        num_envio = float(monto_a_cotizar)
                        if num_recibo > 0:
                            tasa_final = num_recibo / num_envio
                            print(f"    🧮 Tasa calculada: {tasa_final:.6f}")
                            return tasa_final, monto_a_cotizar
            except: pass

            print("    ❌ No se pudo obtener la tasa en Curiara.")
            return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en Curiara: {e}")
            return 0.0, monto_a_cotizar