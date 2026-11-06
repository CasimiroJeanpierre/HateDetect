# HateDetect v3 — integración candidata con bloqueo de despliegue

**Fecha de preparación:** 06/11/2026. **No modificar ni desplegar `main` automáticamente.**

## Evidencia disponible (exploratoria)

- Modelo publicado, SHA-256 `acb50ded09ca2b782210b730c915e3709f75c6767cf8cdebc6189fe6cc324b73`, serializado en scikit-learn **1.9.1**.
- Candidato v3, SHA-256 `7636ab070a11009db24f561d63200ae172f6dd7bd4340a74f881182ed6fd7c1f`, serializado en scikit-learn **1.8.0**.
- En 120 comentarios sintéticos de prueba y referencia **asistida por IA**, Macro-F1 publicado 60,97 % vs v3 89,36 %. No se acredita validación humana independiente ni generalización a Reddit.
- La app `main` fija `scikit-learn==1.9.1`. La versión v3 del binario es **incompatible** con ese entorno sin homologación. No actualizar requisitos a 1.8.0: rompería la compatibilidad del modelo publicado.

## Aplicar sin tocar producción (Windows / PowerShell)

1. Trabajar en el clon correcto `CasimiroJeanpierre/HateDetect`, con `git status --short` vacío. Confirmar que no hay cambios pendientes.
2. `git switch main; git pull --ff-only; git switch -c feature/hatedetect-v3-staging-gated`
3. Desde la carpeta descargada del paquete de integración:

   ```powershell
   python .\apply_staging_patch.py "C:\ruta\a\HateDetect" --dry-run
   python .\apply_staging_patch.py "C:\ruta\a\HateDetect"
   ```
4. `cd C:\ruta\a\HateDetect; python -m pytest tests -q; python -m py_compile app.py auth_google.py model_release.py`
5. `git diff --check` y revisar `git diff`. Crear PR **borrador**, sin fusionar, cuando pase la revisión.

## Funcionamiento seguro

- `HATEDETECT_MODEL_VERSION` sin definir => **published**: modelo previo intacto, `model.pkl` original y metadatos actuales.
- `HATEDETECT_MODEL_VERSION=v3` => exige `assets/model_v3.joblib`, SHA exacto y scikit-learn 1.8.0. Dado que producción usa 1.9.1, este modo **debe fallar de forma controlada**, en vez de cargar un pickle de versión incompatible.
- Las entradas individual y por lotes comparten el clasificador seleccionado. Historial persistente registra la versión activa sin cambiar RLS.
- Nunca descargar binarios desde URL en tiempo de inferencia ni cargar archivos joblib/pickle no verificados.
- El parámetro de versión no se expone en la UI. Para cambiarlo se requiere cambiar configuración y reiniciar proceso.

## Bloqueadores antes de habilitar v3 en Streamlit Cloud

1. Preparar una serialización v3 **compatible con scikit-learn 1.9.1** en un entorno aislado y controlado. El archivo incluido en el paquete se conserva solo como artefacto de comparación **en 1.8.0**.
2. Congelar el **nuevo SHA** y la procedencia del artefacto compatible; actualizar `MODEL_CONFIGS['v3']` tras verificarlo. No usar los 120 comentarios para reajustar hiperparámetros.
3. Probar paridad de predicciones del modelo homologado frente al modelo experimental fijado. Si cambia su comportamiento, documentar nueva versión y necesitar una evaluación independiente adicional antes de aceptar nuevas métricas.
4. Pruebas de regresión: clasificación individual, lotes, CSV mal formado, texto vacío/largo, Unicode, historial Google/Supabase con dos cuentas, roles, RLS, Reportes y CSV. Verificar que solo se procesen entradas sintéticas de prueba.
5. Ejecutar `python -m pytest tests -q` en el entorno exacto de producción (versiones de `requirements.txt`). Probar primero una app Streamlit **de staging distinta** de la publicada, sin mezclar secretos.
6. Plan de reversión: quitar variable `HATEDETECT_MODEL_VERSION` (o poner `published`), reiniciar la instancia de staging y comprobar que el SHA publicado siga siendo el registrado. Para producción, regresar al commit previo si hay falla; nunca conservar una copia contaminada del modelo.

**No se debe fusionar ni desplegar este parche hasta cerrar los bloqueadores.**
