# HateDetect — Clasificación automática por lotes

## Objetivo

Agregar una sección pública de clasificación automática de comentarios **sintéticos** mediante un archivo CSV, utilizando el **mismo modelo TF-IDF + LogisticRegression** que la clasificación individual. **No modifica** la autenticación de Google, RBAC ni RLS; no carga comentarios a Supabase.

## Limitaciones

- CSV UTF-8 (con o sin BOM), delimitador coma `,` o punto y coma `;`.
- Una columna `comentario` (o `texto`, `comment`, `text`) de forma inequívoca.
- 1–500 filas por archivo, tamaño máximo 1 MiB, longitud de texto por fila 2000 caracteres.
- Filas vacías o demasiado largas se señalan como `Omitida`, sin descartar su posición.
- La predicción se efectúa para todos los comentarios válidos en una llamada vectorizada.
- El CSV descargable escapa posibles fórmulas de Excel en textos controlados por usuarios.
- Resultados exclusivamente en estado temporal de la sesión de Streamlit; no persisten en base de datos.
- No hay evaluación de precisión sin etiquetas verdaderas; la gráfica refleja **predicciones**, no calidad del modelo.

## Instalación segura en Windows (PowerShell)

Desde `C:\Users\user\Desktop\HateDetect_Publico_Para_Cloud` (el repositorio **CasimiroJeanpierre/HateDetect**, NO el Capstone principal):

```powershell
git remote -v
git switch main
git pull --ff-only origin main
git switch -c feature/clasificacion-por-lotes
```

Extrae el ZIP en esa misma carpeta, conservando tus archivos existentes:

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\HateDetect_Clasificacion_Lotes.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe .\install_batch.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m py_compile app.py batch_classification.py install_batch.py
```

El instalador se detiene sin modificar `app.py` si no encuentra el `main` con RBAC publicado. No fuerces el parche.

Confirma exactamente qué se publicará:

```powershell
git status --short
git add app.py batch_classification.py install_batch.py tests/test_batch_classification.py GUIA_LOTES.md EJEMPLO_COMENTARIOS_SINTETICOS.csv
git diff --cached --check
git commit -m "Agregar clasificacion automatica por lotes CSV"
git push -u origin feature/clasificacion-por-lotes
```

## Validación antes de producción

Configura la app `hatedetect-upn-pruebas` para usar la rama `feature/clasificacion-por-lotes` (o crea una app adicional de pruebas); no fusiones en `main` hasta completar estos escenarios:

- CSV de ejemplo: clasificación automática y exportación.
- CSV con filas vacías: se indican como omitidas.
- CSV con 501 filas: archivo rechazado.
- CSV con texto de más de 2000 caracteres: omitido.
- El historial persistente sigue funcionando con cuenta `admin`.
- Cuenta no autorizada puede utilizar lotes públicos, pero no acceder al Historial persistente.
- Reportes individuales y clasificación individual siguen operativos.

La clasificación pública por lotes es una **demostración académica** y no debe utilizar datos reales ni determinar sanciones automáticas. El modelo solo genera predicciones exploratorias.
