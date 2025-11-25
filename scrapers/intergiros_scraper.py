from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import time
from data_config import URLS_COMPETIDORES

class IntergirosScraper(BaseScraper):
    def __init__(self, driver):
        # La URL base aquí es genérica, pero usaremos URLs específicas por ruta
        super().__init__(driver, "Intergiros", URLS_COMPETIDORES.get("Intergiros", ""))
        
        # URLs específicas para cada ruta de Intergiros
        self.rutas_urls = {
            "PENVES": "https://www.intergiros.com/peru-a-venezuela-deposito-bancario/",
            "COPVES": "https://www.intergiros.com/colombia-a-venezuela-deposito-bancario/",
            "BRLVES": "https://www.intergiros.com/brasil-a-venezuela/"
        }

    def _handle_popup(self):
        """Intenta cerrar pop-ups promocionales si aparecen."""
        try:
            # Buscar botones de cierre comunes (X, Close, Cerrar)
            selectores_cierre = [
                "//button[contains(@class, 'close')]",
                "//div[contains(@class, 'close')]",
                "//span[contains(text(), '×')]",
                "//button[contains(text(), 'Cerrar')]"
            ]
            
            for selector in selectores_cierre:
                elementos = self.driver.find_elements(By.XPATH, selector)
                for el in elementos:
                    if el.is_displayed():
                        print("    -> Cerrando pop-up detectado...")
                        el.click()
                        time.sleep(1)
                        return
        except Exception:
            # No es crítico si falla, seguimos intentando leer el texto
            pass

    def get_tasa_por_ruta(self, ruta):
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        url = self.rutas_urls.get(ruta)
        if not url:
            print(f"    ❌ Error: No hay URL configurada para la ruta {ruta} en Intergiros")
            return 0.0, "100"
            
        monto_a_cotizar = self._get_monto_a_cotizar(ruta[:3])
        
        try:
            self.driver.get(url)
            # Espera corta para carga inicial
            time.sleep(3)
            
            # Intentar cerrar pop-ups que puedan tapar el contenido
            self._handle_popup()
            
            # Obtener todo el texto del cuerpo de la página
            # Es más fiable buscar en todo el texto que adivinar el selector exacto que cambia a veces
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            tasa_encontrada = 0.0
            
            # Lógica específica por moneda
            if ruta == "PENVES":
                # Patrón típico: "1 Sol = 96.33 Bs."
                match = re.search(r'1\s*Sol\s*=\s*([\d\.]+)\s*Bs', body_text, re.IGNORECASE)
                if match:
                    tasa_encontrada = float(match.group(1))
                    
            elif ruta == "BRLVES":
                # Patrón típico: "1 Real = 6.50 Bs."
                match = re.search(r'1\s*Real\s*=\s*([\d\.]+)\s*Bs', body_text, re.IGNORECASE)
                if match:
                    tasa_encontrada = float(match.group(1))
            
            elif ruta == "COPVES":
                # Colombia suele mostrar la tasa inversa (ej: Tasa = 15 pesos por bolivar)
                # Buscamos: "Tasa = 15" o "10,000 Pesos = 666.66 Bs"
                
                # Intento 1: Tasa directa mostrada como factor de conversión
                match_tasa = re.search(r'Tasa\s*=\s*([\d\.]+)', body_text, re.IGNORECASE)
                
                # Intento 2: Cálculo basado en ejemplo (10,000 Pesos = X Bs)
                match_ejemplo = re.search(r'([\d,]+)\s*Pesos\s*=\s*([\d\.]+)\s*Bs', body_text, re.IGNORECASE)
                
                if match_ejemplo:
                    pesos = float(match_ejemplo.group(1).replace(',', ''))
                    bolivares = float(match_ejemplo.group(2).replace(',', '.'))
                    if pesos > 0:
                        tasa_encontrada = bolivares / pesos
                elif match_tasa:
                    val = float(match_tasa.group(1))
                    # A veces ponen la tasa inversa (COP/VES), a veces directa. 
                    # Si el valor es > 1 (ej: 15), es Pesos por Bolivar -> Tasa directa = 1/15
                    if val > 1:
                        tasa_encontrada = 1 / val
                    else:
                        tasa_encontrada = val

            if tasa_encontrada > 0:
                print(f"    ✅ Tasa encontrada en texto: {tasa_encontrada:.6f}")
                return tasa_encontrada, monto_a_cotizar
            else:
                print("    ⚠️ No se encontró el patrón de texto de la tasa.")
                # Debug: imprimir parte del texto para ver qué falló
                print(f"    🔍 Texto muestra: {body_text[:200].replace(chr(10), ' ')}...")
                return 0.0, monto_a_cotizar

        except Exception as e:
            print(f"    ❌ Error en Intergiros {ruta}: {e}")
            return 0.0, monto_a_cotizar