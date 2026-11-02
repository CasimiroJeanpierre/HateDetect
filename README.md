# HateDetect — demostración pública de Capstone

Publicación independiente del repositorio académico de investigación. Solo se incluyen un clasificador TF-IDF + LogisticRegression **ya entrenado** y métricas agregadas de los cuatro modelos. No contiene corpus de anotación, SQLite de evaluadores, registros de usuarios, historial local ni el checkpoint XLM-RoBERTa.

## Streamlit Community Cloud (gratuito)

1. Crea un **repositorio nuevo y público** en GitHub exclusivamente para los archivos de este directorio (`app.py`, `requirements.txt`, `Dockerfile`, `assets/`, este `README.md`). **No subas la carpeta principal del proyecto ni el contenido de `private/` y `runs/`.**
2. Visita https://share.streamlit.io/ e inicia sesión con GitHub. Haz clic en «Create app».
3. Selecciona tu nuevo repositorio, la rama `main`, y usa `app.py` como archivo de inicio. Escoge Python **3.13** si se ofrece esa opción.
4. Publica y prueba la clasificación, los reportes y el historial **temporal por sesión** desde una segunda computadora o navegador.
5. Conserva capturas de la URL HTTPS, pantalla de clasificación, reportes, y registra la fecha, commit y resultado de QA para el informe académico.

## Alternativa Azure for Students

El mismo directorio contiene `Dockerfile` para una prueba posterior en Azure Container Apps, plan Consumption. Ese servicio tiene una franquicia mensual de recursos, pero *no garantiza un costo total cero*: revisa consumo, configuración de réplicas, almacenamiento, logs, registro de contenedores y presupuesto. No habilites planes de pago permanentes sin revisar estimaciones y límites.

## Límites deliberados de la versión pública

- El Historial es **temporal por sesión**, no persistente. No debe describirse como equivalente a la función local HU-05 hasta agregar identidad/autenticación y almacenamiento persistente seguro.
- Solo se despliega el clasificador seleccionado. Los otros tres modelos se muestran en los reportes mediante sus métricas, pero no ejecutan inferencia en la nube.
- El modelo utiliza textos sintéticos y es experimental; no representa el desempeño real sobre Reddit.
- No cargar `joblib` recibidos de terceros o fuentes no confiables.
- La versión local completa con anotación y entrenamiento permanece separada y privada.
