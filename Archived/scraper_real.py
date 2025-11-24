# scraper_real.py - Scraper específico para extraer tasas reales

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import datetime
import re
import time
from data_config import RUTAS_POR_COMPETIDOR, URLS_COMPETIDORES, MONTOS_POR_MONEDA


def extraer_tasa_de_texto(texto):
    """Extrae la tasa de cambio del texto de la página con patrones más robustos."""
    if not texto:
        return None
        
    # Limpiar texto
    texto_limpio = re.sub(r'\s+', ' ', texto.strip())
    
    # Buscar patrones como "1 VES = 4,03 CLP" o "4,03 CLP = 1 VES"
    patrones = [
        # Patrones directos de tasas
        r'1\s*VES\s*=\s*([\d,\.]+)\s*CLP',  # 1 VES = 4,03 CLP
        r'([\d,\.]+)\s*CLP\s*=\s*1\s*VES',  # 4,03 CLP = 1 VES
        r'([\d,\.]+)\s*CLP\s*por\s*VES',    # 4,03 CLP por VES
        r'tipo\s*de\s*cambio[:\s]*([\d,\.]+)',  # tipo de cambio: 4,03
        r'exchange\s*rate[:\s]*([\d,\.]+)',  # exchange rate: 4,03
        
        # Patrones para montos recibidos
        r'recibe[:\s]*\$?\s*([\d,\.]+)\s*VES',  # recibe: $23.832 VES
        r'recibes[:\s]*\$?\s*([\d,\.]+)\s*VES',  # recibes: $23.832 VES
        r'tu\s*contacto\s*recibe[:\s]*\$?\s*([\d,\.]+)\s*VES',  # tu contacto recibe: $23.832 VES
        
        # Patrones para conversiones
        r'([\d,\.]+)\s*CLP\s*→\s*([\d,\.]+)\s*VES',  # 96.000 CLP → 23.832 VES
        r'([\d,\.]+)\s*CLP\s*convierte\s*a\s*([\d,\.]+)\s*VES',  # 96.000 CLP convierte a 23.832 VES
        
        # Patrones para ratios
        r'ratio[:\s]*([\d,\.]+)',  # ratio: 4.03
        r'rate[:\s]*([\d,\.]+)',   # rate: 4.03
        
        # Patrones para números con decimales
        r'([\d,\.]+)\s*CLP\s*=\s*([\d,\.]+)\s*VES',  # 96.000 CLP = 23.832 VES
        r'([\d,\.]+)\s*VES\s*=\s*([\d,\.]+)\s*CLP',  # 23.832 VES = 96.000 CLP
    ]
    
    for patron in patrones:
        try:
            match = re.search(patron, texto_limpio, re.IGNORECASE)
            if match:
                # Si el patrón tiene 2 grupos, calcular la tasa
                if len(match.groups()) == 2:
                    grupo1 = match.group(1).replace(',', '.')
                    grupo2 = match.group(2).replace(',', '.')
                    try:
                        num1 = float(grupo1)
                        num2 = float(grupo2)
                        if num1 > 0 and num2 > 0:
                            # Calcular tasa: si es CLP → VES, la tasa es num2/num1
                            # Si es VES → CLP, la tasa es num1/num2
                            if 'CLP' in match.group(0) and 'VES' in match.group(0):
                                if 'CLP' in match.group(0)[:match.start()]:
                                    # CLP viene primero, calcular VES/CLP
                                    tasa = num2 / num1
                                else:
                                    # VES viene primero, calcular CLP/VES
                                    tasa = num1 / num2
                                print(f"    🧮 Tasa calculada: {tasa}")
                                return tasa
                    except ValueError:
                        continue
                else:
                    # Un solo grupo, usar directamente
                    tasa_str = match.group(1).replace(',', '.')
                    try:
                        tasa = float(tasa_str)
                        if tasa > 0:
                            print(f"    🧮 Tasa directa: {tasa}")
                            return tasa
                    except ValueError:
                        continue
        except Exception as e:
            continue
    
    # Si no encontramos nada con patrones específicos, buscar cualquier número que parezca una tasa
    numeros = re.findall(r'[\d,\.]+', texto_limpio)
    for numero_str in numeros:
        try:
            numero = float(numero_str.replace(',', '.'))
            # Filtrar números que podrían ser tasas (entre 0.001 y 1000)
            if 0.001 <= numero <= 1000:
                print(f"    🧮 Posible tasa encontrada: {numero}")
                return numero
        except ValueError:
            continue
    
    return None


def calcular_tasa_inversa(tasa_directa):
    """Calcula la tasa inversa (1 / tasa_directa)."""
    if tasa_directa > 0:
        return 1 / tasa_directa
    return 0.0


def scrape_competidor_real(driver, competidor, url, ruta):
    """Hace scraping real de un competidor específico con JavaScript dinámico."""
    print(f"  > Scraping real de {competidor} para ruta {ruta}")
    
    moneda_origen = ruta[:3]
    moneda_destino = ruta[3:]
    monto_a_cotizar = MONTOS_POR_MONEDA.get(moneda_origen, "100")
    
    try:
        print(f"    🌐 Navegando a: {url}")
        driver.get(url)
        
        # Esperar más tiempo para que cargue JavaScript
        time.sleep(5)
        
        # Esperar a que aparezcan elementos dinámicos
        wait = WebDriverWait(driver, 15)
        
        # Intentar interactuar con la página para activar JavaScript
        try:
            # Buscar y hacer clic en elementos que puedan activar las tasas
            elementos_interactivos = [
                "//button[contains(text(), 'Calcular') or contains(text(), 'Cotizar') or contains(text(), 'Convertir')]",
                "//input[@type='number']",
                "//input[contains(@placeholder, 'amount') or contains(@placeholder, 'monto')]",
                "//select",
                "//*[contains(@class, 'calculator') or contains(@class, 'converter')]"
            ]
            
            for selector in elementos_interactivos:
                try:
                    elementos = driver.find_elements(By.XPATH, selector)
                    if elementos:
                        print(f"    🔍 Elemento interactivo encontrado: {selector}")
                        # Intentar hacer clic o interactuar
                        for elemento in elementos[:2]:  # Solo los primeros 2
                            try:
                                if elemento.is_displayed() and elemento.is_enabled():
                                    elemento.click()
                                    time.sleep(2)
                                    break
                            except:
                                continue
                        break
                except:
                    continue
        except:
            pass
        
        # Esperar más tiempo para que se carguen las tasas
        time.sleep(3)
        
        # Buscar tasas con selectores más específicos para JavaScript
        selectores_tasa_js = [
            # Selectores para elementos que contienen tasas
            "//*[contains(@class, 'rate') or contains(@class, 'tasa') or contains(@class, 'exchange')]",
            "//*[contains(@class, 'result') or contains(@class, 'resultado') or contains(@class, 'conversion')]",
            "//*[contains(@class, 'amount') or contains(@class, 'monto') or contains(@class, 'total')]",
            "//*[contains(@class, 'price') or contains(@class, 'precio') or contains(@class, 'value')]",
            # Selectores para texto que contiene números y monedas
            "//*[contains(text(), 'VES') and contains(text(), 'CLP')]",
            "//*[contains(text(), '=') and (contains(text(), 'CLP') or contains(text(), 'VES'))]",
            "//*[contains(text(), 'tipo de cambio') or contains(text(), 'exchange rate')]",
            "//*[contains(text(), 'recibe') or contains(text(), 'recibes')]",
            # Selectores para spans y divs con números
            "//span[contains(text(), '$') or contains(text(), 'CLP') or contains(text(), 'VES')]",
            "//div[contains(text(), '$') or contains(text(), 'CLP') or contains(text(), 'VES')]",
            # Selectores para inputs con valores
            "//input[@value and (contains(@value, 'CLP') or contains(@value, 'VES') or contains(@value, '$'))]"
        ]
        
        tasa_encontrada = None
        
        for i, selector in enumerate(selectores_tasa_js):
            try:
                print(f"    🔍 Probando selector {i+1}/{len(selectores_tasa_js)}: {selector[:50]}...")
                elementos = driver.find_elements(By.XPATH, selector)
                
                for elemento in elementos:
                    try:
                        texto = elemento.text.strip()
                        if texto and len(texto) > 0:
                            print(f"    📝 Texto encontrado: {texto[:100]}...")
                            
                            # Buscar tasa en el texto
                            tasa = extraer_tasa_de_texto(texto)
                            if tasa and tasa > 0:
                                tasa_encontrada = tasa
                                print(f"    ✅ Tasa encontrada: {tasa}")
                                break
                            
                            # También buscar en el atributo value si es un input
                            if elemento.tag_name == 'input':
                                value = elemento.get_attribute('value')
                                if value:
                                    print(f"    📝 Value encontrado: {value[:50]}...")
                                    tasa = extraer_tasa_de_texto(value)
                                    if tasa and tasa > 0:
                                        tasa_encontrada = tasa
                                        print(f"    ✅ Tasa encontrada en value: {tasa}")
                                        break
                    
                    except Exception as e:
                        continue
                
                if tasa_encontrada:
                    break
                    
            except Exception as e:
                print(f"    ❌ Error con selector {i+1}: {e}")
                continue
        
        # Si no encontramos nada, buscar en todo el HTML
        if not tasa_encontrada:
            print(f"    🔍 Buscando en HTML completo...")
            try:
                page_source = driver.page_source
                tasa_encontrada = extraer_tasa_de_texto(page_source)
                if tasa_encontrada:
                    print(f"    ✅ Tasa encontrada en HTML: {tasa_encontrada}")
            except:
                pass
        
        # Si aún no encontramos nada, intentar ejecutar JavaScript
        if not tasa_encontrada:
            print(f"    🔍 Ejecutando JavaScript para buscar tasas...")
            try:
                # Ejecutar JavaScript para buscar elementos con tasas
                js_code = """
                var elementos = document.querySelectorAll('*');
                var tasas = [];
                for (var i = 0; i < elementos.length; i++) {
                    var texto = elementos[i].textContent || elementos[i].innerText || '';
                    if (texto.includes('VES') && texto.includes('CLP') && texto.includes('=')) {
                        tasas.push(texto);
                    }
                }
                return tasas;
                """
                tasas_js = driver.execute_script(js_code)
                if tasas_js:
                    print(f"    📝 JavaScript encontró: {tasas_js}")
                    for texto_js in tasas_js:
                        tasa = extraer_tasa_de_texto(texto_js)
                        if tasa and tasa > 0:
                            tasa_encontrada = tasa
                            print(f"    ✅ Tasa encontrada con JS: {tasa}")
                            break
            except Exception as e:
                print(f"    ❌ Error ejecutando JavaScript: {e}")
            
        if tasa_encontrada:
            print(f"    ✅ Tasa final: {tasa_encontrada}")
            return tasa_encontrada, monto_a_cotizar
        else:
            print(f"    ❌ No se encontró tasa en {competidor}")
            return 0.0, monto_a_cotizar
            
    except Exception as e:
        print(f"    ❌ Error en scraping de {competidor}: {e}")
        return 0.0, monto_a_cotizar


def ejecutar_scraping_real():
    """Ejecuta scraping real de todas las páginas."""
    print("--- INICIANDO SCRAPING REAL ---")
    
    # Configurar Chrome para JavaScript dinámico
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--enable-javascript")  # Asegurar que JS esté habilitado
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--window-size=1920,1080")  # Tamaño de ventana estándar
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = None
    resultados = []
    
    try:
        driver = webdriver.Chrome(options=options)
        
        for competidor, rutas in RUTAS_POR_COMPETIDOR.items():
            url = URLS_COMPETIDORES.get(competidor)
            if not url:
                print(f"  ⚠️ URL no encontrada para {competidor}")
                continue
                
            print(f"\n🏢 Procesando competidor: {competidor}")
            
            for ruta in rutas:
                print(f"  📍 Ruta: {ruta}")
                
                try:
                    tasa_directa, monto_usado = scrape_competidor_real(driver, competidor, url, ruta)
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
                    
                except Exception as e:
                    print(f"    ❌ Error procesando {ruta}: {e}")
                    # Agregar resultado con tasa 0
                    resultado = {
                        'competidor': competidor,
                        'ruta': ruta,
                        'moneda_origen': ruta[:3],
                        'moneda_destino': ruta[3:],
                        'monto_cotizado': MONTOS_POR_MONEDA.get(ruta[:3], "100"),
                        'tasa_directa': 0.0,
                        'tasa_inversa': 0.0,
                        'fecha': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    resultados.append(resultado)
    
    except Exception as e:
        print(f"❌ Error general: {e}")
    finally:
        if driver:
            driver.quit()
    
    # Exportar resultados
    if resultados:
        df = pd.DataFrame(resultados)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        nombre_archivo = f'benchmark_real_{timestamp}.xlsx'
        df.to_excel(nombre_archivo, index=False, sheet_name='Benchmark_Real')
        
        print(f"\n--- RESULTADOS EXPORTADOS ---")
        print(f"📊 Total de registros: {len(resultados)}")
        print(f"📁 Archivo generado: {nombre_archivo}")
        
        # Mostrar tasas encontradas
        tasas_encontradas = [r for r in resultados if r['tasa_directa'] > 0]
        print(f"✅ Tasas reales encontradas: {len(tasas_encontradas)}")
        
        for resultado in tasas_encontradas:
            print(f"  {resultado['competidor']} - {resultado['ruta']}: {resultado['tasa_directa']}")
    
    print("\n--- SCRAPING REAL FINALIZADO ---")


if __name__ == "__main__":
    ejecutar_scraping_real()
