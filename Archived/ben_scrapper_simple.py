# benchmark_excel_simple.py - Versión simplificada que funciona

import pandas as pd
import datetime
import random
from data_config import RUTAS_POR_COMPETIDOR, URLS_COMPETIDORES, MONTOS_POR_MONEDA


def calcular_tasa_inversa(tasa_directa):
    """Calcula la tasa inversa (1 / tasa_directa)."""
    if tasa_directa > 0:
        return 1 / tasa_directa
    return 0.0


def generar_tasa_mock(competidor, ruta):
    """Genera una tasa mock realista basada en el competidor y ruta."""
    # Tasas base por competidor (simulando diferencias reales)
    tasas_base = {
        "Arcadi": 0.0008,
        "Curiara": 0.0009,
        "Global66": 0.0007,
        "Intergiros": 0.0006,
        "Money Gram": 0.0005,
        "Quickxnet": 0.00085,
        "Remesas Vzla": 0.00075,
        "Remittven": 0.0004,
        "RIA": 0.00045,
        "Tucambio CL": 0.0008,
        "Vitawallet": 0.0007,
        "Western Union": 0.0004
    }
    
    # Variación aleatoria del ±20%
    tasa_base = tasas_base.get(competidor, 0.0007)
    variacion = random.uniform(0.8, 1.2)
    return round(tasa_base * variacion, 6)


def ejecutar_benchmark_simple():
    """Versión simplificada que genera datos mock realistas."""
    print("--- INICIANDO BOT DE BENCHMARK SIMPLIFICADO ---")
    print("📝 Generando datos mock realistas...")
    
    resultados = []
    
    for competidor, rutas in RUTAS_POR_COMPETIDOR.items():
        print(f"\n🏢 Procesando competidor: {competidor}")
        
        for ruta in rutas:
            print(f"  📍 Ruta: {ruta}")
            
            # Generar tasa mock realista
            tasa_directa = generar_tasa_mock(competidor, ruta)
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
        
        # Mostrar mejores tasas
        print(f"\n--- MEJORES TASAS (MAYOR VALOR) ---")
        mejores = sorted(resultados, key=lambda x: x['tasa_directa'], reverse=True)[:5]
        for i, resultado in enumerate(mejores, 1):
            print(f"  {i}. {resultado['competidor']} - {resultado['ruta']}: {resultado['tasa_directa']}")
        
        # Mostrar peores tasas
        print(f"\n--- PEORES TASAS (MENOR VALOR) ---")
        peores = sorted(resultados, key=lambda x: x['tasa_directa'])[:5]
        for i, resultado in enumerate(peores, 1):
            print(f"  {i}. {resultado['competidor']} - {resultado['ruta']}: {resultado['tasa_directa']}")
            
    else:
        print("❌ No se obtuvieron resultados para exportar.")
    
    print("\n--- BOT FINALIZADO ---")


if __name__ == "__main__":
    ejecutar_benchmark_simple()
