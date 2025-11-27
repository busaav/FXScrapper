from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time
from data_config import URLS_COMPETIDORES

class XeScraper(BaseScraper):
    def __init__(self, driver):
        # La URL base es solo referencia, usaremos dinámicas
        super().__init__(driver, "XE", "https://www.xe.com/")

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3]
        moneda_destino = ruta[3:]
        
        # Construir URL directa (Siempre Amount=1 para ver la tasa unitaria limpia)
        url_directa = f"https://www.xe.com/currencyconverter/convert/?Amount=1&From={moneda_origen}&To={moneda_destino}"
        
        monto_a_cotizar = self._get_monto_a_cotizar(moneda_origen)
        
        try:
            self.driver.get(url_directa)
            # Espera un poco más larga para que cargue el react/hidratación
            time.sleep(5) 

            # 1. MANEJO DE COOKIES (Si aparecen, aceptar para limpiar pantalla)
            try:
                # Botón "Accept" o "Consent"
                btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Accept')]")
                if btns:
                    btns[0].click()
                    time.sleep(0.5)
            except: pass

            # 2. EXTRAER TASA
            tasa_final = 0.0
            
            try:
                # Buscamos el párrafo con las clases de tu imagen:
                # "text-lg font-semibold text-xe-neutral-900 md:text-2xl"
                # Usamos un selector CSS parcial para ser más robustos si cambian algo leve
                
                # Opción A: Por clases específicas (muy preciso según tu foto)
                selector_css = "p[class*='text-lg'][class*='font-semibold'][class*='text-xe-neutral-900']"
                
                # Esperamos que aparezca
                elemento_tasa = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector_css))
                )
                
                texto_completo = elemento_tasa.text.strip() # Ej: "1.00 EUR = 1.15942393 USD"
                print(f"    -> Texto detectado: '{texto_completo}'")
                
                # Regex para sacar el número después del "="
                # Busca: = (espacio opcional) (número con puntos y comas)
                match = re.search(r'=\s*([\d\.,]+)', texto_completo)
                
                if match:
                    val_str = match.group(1)
                    # XE suele usar formato inglés (1,000.00) por defecto en URL internacional
                    val_clean = val_str.replace(',', '') # Quitar comas de miles
                    
                    tasa_final = float(val_clean)
                    print(f"    ✅ Tasa encontrada: {tasa_final}")

            except Exception as e:
                print(f"    ⚠️ Error extrayendo tasa por clases: {e}")
                
                # Opción B: Fallback por texto "1 [ORIGEN] ="
                try:
                    xpath_texto = f"//*[contains(text(), '1.00 {moneda_origen}') and contains(text(), '=')]"
                    el = self.driver.find_element(By.XPATH, xpath_texto)
                    txt = el.text
                    match = re.search(r'=\s*([\d\.,]+)', txt)
                    if match:
                        tasa_final = float(match.group(1).replace(',', ''))
                        print(f"    ✅ Tasa encontrada (Fallback Texto): {tasa_final}")
                except: pass

            if tasa_final > 0:
                return tasa_final, monto_a_cotizar

            return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error crítico en XE: {e}")
            return 0.0, monto_a_cotizar