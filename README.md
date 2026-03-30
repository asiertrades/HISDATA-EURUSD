# HISDATA-EURUSD

Biblioteca de datos históricos del tipo de cambio EUR/USD desde 2000 hasta 2025.

## Descripción

Este repositorio contiene archivos CSV con datos históricos del euro frente al dólar estadounidense (EUR/USD) para cada año desde el 2000 hasta 2025. Cada archivo contiene información del mes de enero del año correspondiente.

Esta es una **biblioteca de datos** diseñada para ser utilizada por otros repositorios.

## Estructura

```
data/
├── 2000/
│   └── january.csv
├── 2001/
│   └── january.csv
├── ...
└── 2025/
    └── january.csv
```

## Cómo usar los datos

### Opción 1: Acceder vía URL raw (Recomendado)

Accede directamente a cualquier archivo CSV usando la URL raw de GitHub:

```
https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/data/YYYY/january.csv
```

**Ejemplo:**
```
https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/data/2024/january.csv
```

### Opción 2: Git Submodule

Incluye este repositorio como submódulo en tu proyecto:

```bash
git submodule add https://github.com/asiertrades/hisdata-eurusd.git data/hisdata
```

Luego accede a los archivos localmente:
```bash
cat data/hisdata/data/2024/january.csv
```

### Opción 3: Clonar manualmente

```bash
git clone https://github.com/asiertrades/hisdata-eurusd.git
```

## Formato de los CSV

Cada archivo CSV contiene datos históricos con la siguiente estructura:

- **Fecha** - Fecha del dato
- **Apertura** - Precio de apertura
- **Máximo** - Precio máximo del día
- **Mínimo** - Precio mínimo del día
- **Cierre** - Precio de cierre
- **Volumen** - Volumen de transacciones (si aplica)

**Nota:** Consulta los archivos específicos para confirmar las columnas exactas.

## Ejemplos de uso

### Python
```python
import pandas as pd

url = "https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/data/2024/january.csv"
df = pd.read_csv(url)
print(df.head())
```

### JavaScript/Node.js
```javascript
fetch('https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/data/2024/january.csv')
  .then(response => response.text())
  .then(data => console.log(data));
```

### cURL
```bash
curl https://raw.githubusercontent.com/asiertrades/hisdata-eurusd/main/data/2024/january.csv
```

## Licencia

[Especifica la licencia según corresponda]

## Contribuciones

Para reportar errores o sugerir mejoras, abre un issue en este repositorio.
