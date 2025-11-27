import pandas as pd
from selenium import webdriver
import datetime
import re
from data_config import RUTAS_POR_COMPETIDOR, URLS_COMPETIDORES
# Importar la clase base y las clases específicas
from scrapers.base_scraper import BaseScraper 
from scrapers.global66_api import Global66ApiScraper 
from scrapers.arcadi_api import ArcadiApiScraper
from scrapers.intergiros_scraper import IntergirosScraper
from scrapers.quickex_scraper import QuickexScraper
from scrapers.tucambio_scraper import TuCambioScraper
from scrapers.remesasvzla_scraper import RemesasVzlaScraper
from scrapers.curiara_scrapper import CuriaraScraper
#from scrapers.mipapaya_scraper import MiPapayaScraper
from scrapers.paysend_scraper import PaysendScraper
from scrapers.xe_scraper import XeScraper
# Agrega aquí las clases de otros competidores a medida que las crees
# from scrapers.arcadi_scraper import ArcadiScraper 

# --- Mapeo de Competidores a sus Clases Scraper ---
# Esto permite al bucle principal saber qué clase usar para cada competidor.
COMPETIDOR_MAPPER = {
    #"Global66": Global66ApiScraper,
    #"Arcadi": ArcadiApiScraper,
    #"Intergiros": IntergirosScraper,
    #"Quickex": QuickexScraper,
    #"Tucambio CL": TuCambioScraper,
    #"Remesas Vzla": RemesasVzlaScraper,
    #"Curiara": CuriaraScraper,
    #"Mi Papaya": MiPapayaScraper,
    #"Paysend": PaysendScraper,
    "XE": XeScraper
}

def calcular_tasa_inversa(tasa_directa):
    """Calcula la tasa inversa (1 / tasa_directa)."""
    if tasa_directa > 0:
        return 1 / tasa_directa
    return 0.0

def ejecutar_benchmark_a_excel():
    
    options = webdriver.ChromeOptions()
    options.add_argument("--incognito") 
    
    try:
        # Inicialización del driver
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"ERROR: No se pudo iniciar el WebDriver. Asegúrate de tener ChromeDriver en tu PATH. Detalle: {e}")
        return

    print("--- INICIANDO BOT DE BENCHMARK ---")
    
    resultados = []

    for competidor, rutas in RUTAS_POR_COMPETIDOR.items():
        
        # 1. Seleccionar la clase Scraper correcta
        ScraperClass = COMPETIDOR_MAPPER.get(competidor, None)
        
        if ScraperClass is None:
            # Si el competidor no está en el mapper, lo saltamos
            print(f"  ⚠️ Clase Scraper no definida para {competidor}. Saltando.")
            continue 

        # 2. Inicializar el Scraper (la URL ya está definida en su clase o data_config)
        scraper = ScraperClass(driver) 
        
        # 3. Iterar sobre las rutas definidas para ese competidor
        for ruta in rutas:
            # Llama al método específico de la clase (ej. Global66Scraper.get_tasa_por_ruta)
            tasa_directa, monto_usado = scraper.get_tasa_por_ruta(ruta) 
            tasa_inversa = calcular_tasa_inversa(tasa_directa)
            
            moneda_origen = ruta[:3] 
            
            resultados.append({
                'Fecha': datetime.date.today().isoformat(),
                'Competidor': competidor,
                'Ruta': ruta,
                'Moneda_Origen': moneda_origen,
                'Monto_Cotizado': monto_usado, 
                'Tasa_Directa': tasa_directa,
                'Tasa_Inversa': tasa_inversa,
                'Status': 'OK' if tasa_directa > 0 else 'FALLO'
            })
            
    driver.quit()
    print("--- BENCHMARK FINALIZADO ---")
    
    # --- EXPORTAR A EXCEL ---
    df = pd.DataFrame(resultados)
    nombre_archivo = f"Benchmark_Tasas_{datetime.date.today().isoformat()}.xlsx"
    
    try:
        df.to_excel(nombre_archivo, index=False)
        print(f"\n✅ DATOS EXPORTADOS EXITOSAMENTE a: {nombre_archivo}")
    except Exception as e:
        print(f"\n🛑 ERROR al exportar a Excel: {e}")


if __name__ == "__main__":
    ejecutar_benchmark_a_excel()