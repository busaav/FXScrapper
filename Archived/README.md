# Benchmark Scraper

Script para hacer benchmark de tasas de cambio de múltiples competidores y exportar resultados a Excel.

## 🚀 Uso

### Modo Simplificado (Recomendado - Datos Mock Realistas)
```bash
python ben_scrapper.py
```

### Modo Test (Datos Mock Aleatorios)
```bash
python ben_scrapper.py --test
```

### Modo Real (Scraping - Requiere ChromeDriver)
```bash
python ben_scrapper.py --real
```

### Versión Simplificada (Solo Mock Realistas)
```bash
python ben_scrapper_simple.py
```

## 📋 Características

- **Múltiples modos de ejecución** (simplificado, test, real)
- **Datos mock realistas** basados en competidores reales
- **Exportación a Excel** con timestamp
- **Scraping automático** (modo real) con múltiples selectores
- **Manejo robusto de errores**
- **Logging detallado** del progreso
- **Análisis de mejores/peores tasas**

## 🔧 Requisitos

- Python 3.7+
- Dependencias: `pandas`, `selenium` (solo para modo real)
- ChromeDriver (solo para modo real)

## 📊 Salida

El script genera un archivo Excel con:
- Competidor
- Ruta de cambio
- Monedas origen/destino
- Monto cotizado
- Tasa directa
- Tasa inversa
- Timestamp

## 🛠️ Solución de Problemas

### Errores USB/Chrome
Los errores USB que aparecen en consola son normales y no afectan el funcionamiento.

### Script se cuelga (modo real)
- Usa el modo simplificado por defecto: `python ben_scrapper.py`
- Para testing: `python ben_scrapper.py --test`
- Verifica que ChromeDriver esté instalado para modo real

### No encuentra elementos (modo real)
El script intenta múltiples selectores automáticamente. Si falla, usa el modo simplificado para generar datos realistas.

### Recomendación
**Usa el modo simplificado por defecto** - genera datos mock realistas sin problemas de scraping.
