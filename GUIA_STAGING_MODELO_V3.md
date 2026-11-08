# HateDetect v3 - Integracion controlada en staging

## 1. Alcance

Integracion del candidato v3 sin modificar automaticamente la rama
main ni la aplicacion publicada de Streamlit.

## 2. Modelos

### Modelo publicado
- Archivo: assets/model.pkl
- Scikit-learn: 1.9.1
- SHA-256:
  acb50ded09ca2b782210b730c915e3709f75c6767cf8cdebc6189fe6cc324b73

### Modelo v3 original
- Scikit-learn: 1.8.0
- SHA-256:
  7636ab070a11009db24f561d63200ae172f6dd7bd4340a74f881182ed6fd7c1f

### Modelo v3 homologado
- Archivo: assets/model_v3.joblib
- Scikit-learn: 1.9.1
- SHA-256:
  1b8d300ee3682437b724a2eccf8b9626526280e35e06c7cdaafe216843fe0470
- Entrenamiento reproducido con 432 comentarios sinteticos.
- Arquitectura: TF-IDF de caracteres y LogisticRegression.
- No se utilizaron los 120 ejemplos reservados para reentrenar.

## 3. Evidencia de homologacion

- Comparacion entre v3 original y homologado: 440 predicciones.
- Coincidencia de etiquetas: 440 de 440.
- Diferencias de categorias: 0.
- No se ha demostrado equivalencia universal de probabilidades.

## 4. Evaluacion exploratoria anterior

Sobre 120 comentarios sinteticos con referencia asistida por IA:
- Macro-F1 modelo publicado: 60.97 %.
- Macro-F1 candidato v3: 89.36 %.

Estos resultados no representan una validacion humana independiente
ni permiten afirmar rendimiento equivalente sobre Reddit real.

## 5. Pruebas de staging

- 33 pruebas automatizadas aprobadas.
- Carga real de published y v3 verificada.
- Clasificacion individual comprobada.
- Clasificacion por lotes comprobada con CSV de ejemplo.
- Reportes historicos visibles.
- Guardado y consulta de Historial temporal comprobados.

La seccion Reportes presenta metricas del experimento historico
de 72 comentarios, no las metricas de v3.

## 6. Limitaciones conocidas

- "hola" fue clasificado como Ofensivo.
- "QUE HACES" y "¿Que haces?" fueron clasificados como Ofensivo.
- Ambos casos son falsos positivos cualitativos.
- Las probabilidades del clasificador no estan calibradas.

No introducir reglas artificiales ni reentrenar con la prueba
reservada para ocultar estos errores.

## 7. Pruebas pendientes

- Eliminacion de Historial temporal.
- Google OAuth y persistencia en Supabase.
- Permisos de usuarios, roles y politicas RLS.
- CSV invalidos, filas vacias y limites de procesamiento.
- Verificacion de un despliegue de staging independiente.
- Revision de calidad antes de una promocion a produccion.

## 8. Activacion y reversión

Por defecto: HATEDETECT_MODEL_VERSION=published
Para pruebas aisladas: HATEDETECT_MODEL_VERSION=v3

Ambos artefactos se comprueban mediante SHA-256 y version
de scikit-learn antes de deserializarse.

Para regresar al modelo publicado, detener la instancia local,
establecer HATEDETECT_MODEL_VERSION=published y reiniciar.

NO fusionar con main ni desplegar en produccion
hasta completar la revision de calidad y seguridad.
