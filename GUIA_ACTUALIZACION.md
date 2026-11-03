# HateDetect — mejora de Historial seguro (rama de desarrollo)

## Qué cambia

- Botón Google Identity Services en Streamlit Components v2.
- Supabase Auth verifica **en el servidor** el ID token de Google y genera sesión de usuario.
- Cliente Supabase individual por sesión; ningún cliente autenticado en caché global.
- Base `hatedetect_history` ya creada con RLS y políticas `auth.uid() = user_id`.
- Guardar, consultar y borrar el Historial persistente por usuario.
- Clasificación pública y reportes continúan disponibles sin inicio de sesión.
- Reportes incluyen precisión/recall, exactitud balanceada y exportación CSV.

## Seguridad

- No se necesita `service_role` en ningún sitio.
- No se necesita Client Secret de Google en Streamlit: **solo en Supabase**.
- Únicamente se usa el Google Client ID y la **clave publicable** de Supabase.
- Nunca introduzcas credenciales reales en archivos rastreados por Git.
- No se envían tokens mediante URLs; el botón entrega la credencial por el canal de componentes Streamlit.
- Se requiere internet para cargar Google Identity Services desde `accounts.google.com`.
- Google debe tener configurado el origen JavaScript de la aplicación para la página en que se use.
- Si el dominio de pruebas es diferente al dominio público, añádelo a los **orígenes JavaScript autorizados** en Google Cloud.
- Sesión de aplicación en memoria: si recargas, puede ser necesario entrar con Google de nuevo; los registros **sí** permanecen en Supabase.
- No se ha probado Google OAuth de extremo a extremo hasta que un usuario real complete la validación.
- Los modelos son experimentales y el conjunto de prueba es reducido.

## Instalar en la rama creada

1. Verifica `git branch --show-current` => `feature/historial-seguro-reportes`.
2. Copia **solo** `app.py`, `auth_google.py`, `requirements.txt`, `GUIA_ACTUALIZACION.md`, `.streamlit/secrets.example.toml` y `tests/` a la raíz del proyecto existente.
3. NO borres `assets/model.pkl` ni `assets/summary.json`.
4. `python -m pip install -r requirements.txt` en tu entorno virtual del proyecto (Python 3.13).
5. Prueba localmente: `python -m streamlit run app.py`. Sin `secrets.toml` la clasificación funciona y el botón de Google permanece deshabilitado.
6. `python -m pytest tests -q`. El proyecto debe tener pytest instalado para la prueba.
7. Prueba primero en **otra app de Streamlit** asociada a la rama de desarrollo, no en el enlace público principal.
8. En Streamlit Cloud -> configuración de la app de pruebas -> `Secrets`, pega el contenido del archivo de ejemplo con las dos claves públicas correctas. Nunca uses Client Secret en esos campos.
9. Google Auth Platform -> OAuth client -> orígenes autorizados: agrega también el origen de la **app de pruebas** si el dominio es distinto.
10. Confirma con dos cuentas de Google: guardar, cerrar sesión, volver a entrar, historial persistente, aislamiento cruzado y eliminación selectiva.
11. Solo después integra por PR en `main`.

## Prueba y rollback

- No modifiques el despliegue `https://hatedetect-upn.streamlit.app/` mientras falten pruebas.
- La copia de pruebas sirve para validar Google, Supabase y el flujo de RLS.
- Si falla la nueva app, el despliegue principal sigue en `main` y no se modifica.

## Limitación pendiente

Los reportes detallados del corpus y la ejecución web de los demás modelos necesitan artefactos públicos adicionales, validados y sin datos privados. Este paquete no declara que esas funcionalidades estén completas ni que se haya alcanzado el 100% de los requisitos de la rúbrica.
