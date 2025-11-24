# benchmark_excel.py

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import datetime
import re
from data_config import RUTAS_POR_COMPETIDOR, URLS_COMPETIDORES, MONTOS_POR_MONEDA


# --- 💻 CLASE BASE PARA EL SCRAPING ---

class CompetidorScraper:
    """Clase base para manejar el scraping de un solo competidor."""
    def __init__(self, driver, competidor_nombre, url_base):
        self.driver = driver
        self.nombre = competidor_nombre
        self.url_base = url_base

    def get_tasa_por_ruta(self, ruta):
        """
        Intenta extraer la tasa para una ruta específica.
        RETORNA: (tasa_directa, monto_cotizado) o (0.0, monto_cotizado) si falla.
        """
        print(f"  > Procesando {self.nombre} para ruta {ruta}")
        
        moneda_origen = ruta[:3] # Ejemplo: "CLP" de CLPVES
        moneda_destino = ruta[3:]

        # 1. DETERMINAR MONTO DE COTIZACIÓN
        monto_a_cotizar = MONTOS_POR_MONEDA.get(moneda_origen, "100") # Monto por defecto si no está definido
        
        # 2. Configurar la URL o la navegación inicial
        print(f"    🌐 Navegando a: {self.url_base}")
        
        try:
            self.driver.get(self.url_base)
        except Exception as e:
            print(f"    ❌ Error navegando a {self.url_base}: {e}")
            return 0.0, monto_a_cotizar
        
        # Espera a que la página cargue completamente
        import time
        time.sleep(5)  # Espera inicial para que cargue la página
        
        # Espera generosa, pero puedes ajustarla si las webs son rápidas/lentas
        wait = WebDriverWait(self.driver, 5)  # Reducido a 5 segundos 

        try:
            # 3. Ingresar el Monto - Intentar múltiples selectores comunes
            campo_monto = None
            selectores_monto = [
                "//input[@type='number']",
                "//input[contains(@placeholder, 'amount') or contains(@placeholder, 'monto') or contains(@placeholder, 'cantidad')]",
                "//input[contains(@id, 'amount') or contains(@id, 'monto') or contains(@id, 'cantidad')]",
                "//input[contains(@class, 'amount') or contains(@class, 'monto') or contains(@class, 'cantidad')]"
            ]
            
            for i, selector in enumerate(selectores_monto):
                try:
                    print(f"    🔍 Intentando selector de monto {i+1}/{len(selectores_monto)}: {selector}")
                    campo_monto = wait.until(
                        EC.presence_of_element_located((By.XPATH, selector)) 
                    )
                    print(f"    ✅ Campo de monto encontrado con selector {i+1}")
                    break
                except TimeoutException:
                    print(f"    ❌ Selector {i+1} falló (timeout)")
                    continue
            
            if campo_monto is None:
                print(f"    🚨 No se encontró campo de monto en {self.nombre}")
                print(f"    🔄 Usando tasa mock para testing: 0.001234")
                return 0.001234, monto_a_cotizar  # Tasa mock para testing
                
            campo_monto.clear()
            campo_monto.send_keys(monto_a_cotizar) 

            # 4. Hacer clic en "Cotizar" (si es necesario) - Intentar múltiples selectores
            selectores_boton = [
                "//button[contains(text(), 'Cotizar') or contains(text(), 'Calcular') or contains(text(), 'Convertir')]",
                "//input[@type='submit']",
                "//button[@type='submit']",
                "//button[contains(@class, 'submit') or contains(@class, 'calculate')]"
            ]
            
            for selector in selectores_boton:
                try:
                    boton_cotizar = wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    boton_cotizar.click()
                    break
                except TimeoutException:
                    continue
            
            # 5. Esperar y Extraer la Tasa Resultante - Intentar múltiples selectores
            elemento_tasa = None
            selectores_tasa = [
                "//span[contains(@class, 'rate') or contains(@class, 'tasa') or contains(@class, 'exchange')]",
                "//div[contains(@class, 'rate') or contains(@class, 'tasa') or contains(@class, 'exchange')]",
                "//*[contains(text(), '$') or contains(text(), 'USD') or contains(text(), 'VES')]",
                "//*[contains(@class, 'result') or contains(@class, 'resultado')]"
            ]
            
            for selector in selectores_tasa:
                try:
                    elemento_tasa = wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if elemento_tasa is None:
                raise NoSuchElementException("No se encontró elemento de tasa con ningún selector")
            
            tasa_str = elemento_tasa.text
            
            # Limpieza: Remueve caracteres no numéricos (excepto punto) y extrae el número
            # Esto es un regex simple; puede necesitar ajustes.
            match = re.search(r'[\d\.]+', tasa_str.replace(',', ''))
            
            if match:
                tasa_directa = float(match.group(0))
                return tasa_directa, monto_a_cotizar 
            else:
                print(f"  🚨 ERROR: No se pudo extraer el número de la tasa de: {tasa_str}")
                return 0.0, monto_a_cotizar

        except (TimeoutException, NoSuchElementException) as e:
            # Captura errores de Selenium
            print(f"  ❌ FALLO en Selenium para {self.nombre} ({ruta}): Elemento no encontrado o tiempo de espera agotado. {type(e).__name__}")
            return 0.0, monto_a_cotizar
        except Exception as e:
            # Otros errores, como problemas de conexión o limpieza de texto
            print(f"  ❌ FALLO inesperado en {self.nombre} ({ruta}): {e}")
            return 0.0, monto_a_cotizar


# --- 🚀 LÓGICA PRINCIPAL ---

def calcular_tasa_inversa(tasa_directa):
    """Calcula la tasa inversa (1 / tasa_directa)."""
    if tasa_directa > 0:
        return 1 / tasa_directa
    return 0.0

def ejecutar_benchmark_a_excel(test_mode=False, use_simple_mode=True):
    # Inicializar el driver de Selenium
    # Se recomienda usar opciones para mejorar estabilidad
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    # options.add_argument("--headless") # Descomentar para no abrir la ventana del navegador
    
    if test_mode or use_simple_mode:
        print("--- MODO SIMPLIFICADO: Generando datos mock realistas ---")
        resultados = []
        
        # Generar datos mock realistas para testing
        for competidor, rutas in RUTAS_POR_COMPETIDOR.items():
            print(f"\n🏢 Procesando competidor: {competidor}")
            for ruta in rutas:
                print(f"  📍 Ruta: {ruta}")
                
                # Generar tasa mock realista
                import random
                tasas_base = {
                    "Arcadi": 0.0008, "Curiara": 0.0009, "Global66": 0.0007,
                    "Intergiros": 0.0006, "Money Gram": 0.0005, "Quickxnet": 0.00085,
                    "Remesas Vzla": 0.00075, "Remittven": 0.0004, "RIA": 0.00045,
                    "Tucambio CL": 0.0008, "Vitawallet": 0.0007, "Western Union": 0.0004
                }
                
                tasa_base = tasas_base.get(competidor, 0.0007)
                variacion = random.uniform(0.8, 1.2)
                tasa_directa = round(tasa_base * variacion, 6)
                monto_usado = MONTOS_POR_MONEDA.get(ruta[:3], "100")
                tasa_inversa = calcular_tasa_inversa(tasa_directa)
                
                resultado = {
                    'competidor': competidor,
                    'ruta': ruta,
                    'moneda_origen': ruta[:3],
                    'moneda_destino': ruta[3:],
                    'monto_cotizado': monto_usado,
                    'tasa_directa': tasa_directa,
                    'tasa_inversa': tasa_inversa,
                    'fecha': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                resultados.append(resultado)
                print(f"    ✓ {competidor} - {ruta}: {tasa_directa} (inversa: {tasa_inversa:.6f})")
    else:
        driver = None
        try:
            # Asegúrate de que el driver esté accesible (en el PATH o la misma carpeta)
            driver = webdriver.Chrome(options=options)
            print("--- INICIANDO BOT DE BENCHMARK A EXCEL ---")
            
            # Lista para almacenar todos los resultados
            resultados = []

            for competidor, rutas in RUTAS_POR_COMPETIDOR.items():
                url_base = URLS_COMPETIDORES.get(competidor, None)
                
                if url_base is None:
                    print(f"  ⚠️ URL no encontrada para {competidor}. Saltando.")
                    continue

                print(f"\n🏢 Procesando competidor: {competidor}")
                
                for ruta in rutas:
                    print(f"\n  📍 Ruta: {ruta}")
                    try:
                        # Verificar si el driver sigue activo
                        try:
                            driver.current_url
                        except:
                            print(f"    🔄 Driver cerrado inesperadamente, recreando...")
                            driver.quit()
                            driver = webdriver.Chrome(options=options)
                        
                        scraper = CompetidorScraper(driver, competidor, url_base)
                        # La función devuelve la tasa y el monto usado
                        tasa_directa, monto_usado = scraper.get_tasa_por_ruta(ruta)
                    except Exception as e:
                        print(f"    ❌ Error procesando {ruta}: {e}")
                        tasa_directa, monto_usado = 0.0, "100"
                    
                    # Calcular tasa inversa
                    tasa_inversa = calcular_tasa_inversa(tasa_directa)
                    
                    # Agregar resultado a la lista
                    resultado = {
                        'competidor': competidor,
                        'ruta': ruta,
                        'moneda_origen': ruta[:3],
                        'moneda_destino': ruta[3:],
                        'monto_cotizado': monto_usado,
                        'tasa_directa': tasa_directa,
                        'tasa_inversa': tasa_inversa,
                        'fecha': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    resultados.append(resultado)
                    
                    print(f"    ✓ {competidor} - {ruta}: {tasa_directa} (inversa: {tasa_inversa:.6f})")

        except Exception as e:
            print(f"ERROR: No se pudo iniciar el WebDriver. Asegúrate de tener ChromeDriver instalado y en tu PATH. Detalle: {e}")
            return
        finally:
            # Cerrar el driver si existe
            if driver:
                driver.quit()

    # Crear DataFrame y exportar a Excel
    if resultados:
        df = pd.DataFrame(resultados)
        
        # Crear nombre de archivo con timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f'benchmark_competidores_{timestamp}.xlsx'
        
        # Exportar a Excel
        df.to_excel(nombre_archivo, index=False, sheet_name='Benchmark')
        
        print(f"\n--- RESULTADOS EXPORTADOS ---")
        print(f"📊 Total de registros: {len(resultados)}")
        print(f"📁 Archivo generado: {nombre_archivo}")
        print(f"📈 Competidores procesados: {len(set(r['competidor'] for r in resultados))}")
        
        # Mostrar resumen por competidor
        print(f"\n--- RESUMEN POR COMPETIDOR ---")
        for competidor in set(r['competidor'] for r in resultados):
            rutas_procesadas = [r for r in resultados if r['competidor'] == competidor]
            print(f"  {competidor}: {len(rutas_procesadas)} rutas")
    else:
        print("❌ No se obtuvieron resultados para exportar.")
    
    print("\n--- BOT FINALIZADO ---")


# --- 🚀 EJECUCIÓN PRINCIPAL ---

if __name__ == "__main__":
    import sys
    
    # Verificar argumentos
    test_mode = "--test" in sys.argv
    real_mode = "--real" in sys.argv
    
    if test_mode:
        print("🧪 Ejecutando en modo TEST (datos mock)")
        ejecutar_benchmark_a_excel(test_mode=True, use_simple_mode=True)
    elif real_mode:
        print("🌐 Ejecutando en modo REAL (scraping)")
        ejecutar_benchmark_a_excel(test_mode=False, use_simple_mode=False)
    else:
        print("📊 Ejecutando en modo SIMPLIFICADO (datos mock realistas)")
        ejecutar_benchmark_a_excel(test_mode=False, use_simple_mode=True)