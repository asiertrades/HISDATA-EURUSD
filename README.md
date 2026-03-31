# HISDATA-EURUSD

Biblioteca de datos históricos de tasas de cambio EUR/USD a nivel de minuto desde 2000 hasta 2025.

## Descripción

Este repositorio contiene archivos CSV con datos históricos del tipo de cambio EUR/USD en formato de minuto (M1) para cada año de 2000 a 2025. 

Esta es una **biblioteca de datos pública** diseñada para ser utilizada por otros repositorios como fuente de datos históricos de divisas.

## Contenido

26 archivos CSV (uno por año) con datos de:
- **Período:** 2000 - 2025
- **Granularidad:** Minuto (M1)
- **Pares:** EUR/USD
- **Tamaño total:** ~8.7 MB

### Estructura de archivos

```
DAT_ASCII_EURUSD_M1_2000.csv
DAT_ASCII_EURUSD_M1_2001.csv
...
DAT_ASCII_EURUSD_M1_2025.csv
```

## Formato de datos

Cada CSV contiene datos en el siguiente formato:

```
YYYYMMDD HHMMSS;open;high;low;close;volume
```

**Ejemplo:**
```
20240101 170000;1.104270;1.104290;1.104250;1.104290;0
20240101 170100;1.104290;1.104290;1.104290;1.104290;0
```

**Columnas:**
- `Fecha y Hora` - Formato: YYYYMMDD HHMMSS
- `open` - Precio de apertura
- `high` - Precio máximo del minuto
- `low` - Precio mínimo del minuto
- `close` - Precio de cierre
- `volume` - Volumen (típicamente 0)

## Cómo usar los datos

### Opción 1: URL Raw (Recomendado)

Accede directamente a cualquier archivo CSV desde cualquier aplicación:

```
https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/DAT_ASCII_EURUSD_M1_YYYY.csv
```

**Ejemplo:**
```
https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/DAT_ASCII_EURUSD_M1_2024.csv
```

### Opción 2: Git Submodule

Incluye este repositorio como submódulo en tu proyecto:

```bash
git submodule add https://github.com/asiertrades/hisdata-eurusd.git data/hisdata
```

Luego accede a los archivos:
```bash
cat data/hisdata/DAT_ASCII_EURUSD_M1_2024.csv
```

### Opción 3: Clonar

```bash
git clone https://github.com/asiertrades/hisdata-eurusd.git
```

## Ejemplos de uso

### Python con Pandas

```python
import pandas as pd

url = "https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/DAT_ASCII_EURUSD_M1_2024.csv"
df = pd.read_csv(url, sep=';', header=None, 
                  names=['datetime', 'open', 'high', 'low', 'close', 'volume'])
df['datetime'] = pd.to_datetime(df['datetime'])
print(df.head())
```

### JavaScript/Node.js

```javascript
fetch('https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/DAT_ASCII_EURUSD_M1_2024.csv')
  .then(response => response.text())
  .then(data => {
    const lines = data.trim().split('\n');
    const rows = lines.map(line => {
      const [datetime, open, high, low, close, volume] = line.split(';');
      return { datetime, open, high, low, close, volume };
    });
    console.log(rows);
  });
```

### cURL

```bash
curl https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/DAT_ASCII_EURUSD_M1_2024.csv | head -10
```

## Descubrir archivos disponibles

Usa el archivo `index.json` para obtener la lista completa de archivos disponibles:

```bash
curl https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/index.json
```

## Licencia

[Especifica según corresponda]

## Contribuciones

Para reportar errores o sugerir mejoras, abre un issue en este repositorio.
