# HateDetect — control de roles para el Historial privado

## Alcance

- La sección Clasificación (con comentarios sintéticos) y Reportes siguen siendo **demostración pública**.
- El Historial persistente, guardado y eliminación en Supabase se habilitan **solo para `admin` o `moderator` activos**.
- Los `evaluator` autenticados no tienen acceso al Historial privado: el módulo de anotación no está disponible en esta demostración.
- Una persona autenticada pero no aprobada recibe «Cuenta sin autorización». No obtiene permisos por iniciar sesión con Google.
- La interfaz oculta funciones privadas, y **RLS valida independientemente cada operación** de base de datos.
- Administrar usuarios y cambiar roles sigue siendo una operación restringida del administrador de Supabase mediante SQL Editor; **no hay panel para gestionar roles en la aplicación**.

## 1. Instalar en una rama NUEVA

Desde PowerShell, carpeta `HateDetect_Publico_Para_Cloud`:

```powershell
# Si estabas en la rama antigua, volver al main ya fusionado:
git switch main
git pull origin main
git switch -c feature/autorizacion-moderadores
```

Extraer este ZIP dentro de `HateDetect_Publico_Para_Cloud`, conservando los archivos existentes, especialmente `app.py`, `auth_google.py` y `assets/`.

```powershell
.\.venv\Scripts\python.exe .\install_rbac.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m py_compile app.py auth_google.py access_roles.py
```

Si el instalador muestra «patrón no compatible», **no fuerces cambios**: el código publicado no coincide con el PR #1. Solicita revisión de los archivos actuales.

## 2. Desplegar en rama de prueba

```powershell
git add app.py access_roles.py install_rbac.py tests/test_access_roles.py GUIA_ROLES.md supabase_rls_roles.sql
git diff --cached --check
git commit -m "Incorporar RBAC y proteger Historial privado"
git push -u origin feature/autorizacion-moderadores
```

En Streamlit, utiliza una app de **pruebas** con esa rama (o cambia temporalmente la rama de la app de pruebas existente). No cambies `main` ni la app oficial aún.

Con Google, verifica: a) usuario admin ve Historial persistente; b) usuario sin permiso solo demostración; c) evaluador carece de permiso de Historial; d) sesión revocada deja de ver funciones privadas en el siguiente rerun; e) funcionamiento público de Clasificación/Reportes. No ingreses comentarios personales ni confidenciales.

## 3. Refuerzo de la base (DESPUÉS de validar la app de pruebas)

Ejecutar `supabase_rls_roles.sql` mediante Supabase SQL Editor. La migración sustituye las tres políticas de Historial con verificaciones de pertenencia a la allowlist **en la base**, de forma atómica. Antes de ejecutar, comprueba que exista al menos un `admin` activo.

Después ejecutar prueba de usuarios: admin puede insertar/consultar/eliminar sus registros, cuenta sin autorización no puede (tampoco mediante API), otro moderador solo sus registros, revocación `active=false` impide nuevos accesos. Conservar evidencias.

**¡Importante!** La primera aplicación oficial todavía tiene código sin chequeo de roles. En cuanto se aplique el SQL, la RLS restringirá el acceso aunque la interfaz siga ofreciendo acciones. Por ello debe coordinarse con la integración y probarse sin afectar a terceros.

## 4. Integrar a main

Realizar PR a `main`, revisar que no haya `secrets.toml` ni claves, fusionar y comprobar despliegue oficial. Este paquete **no modifica** directamente el código remoto ni las políticas existentes hasta que se ejecute el SQL de forma explícita.

## 5. Administrar usuarios autorizados (desde SQL Editor con permisos de administrador de Supabase)

Para autorizar un moderador que ya se autenticó con Google:

```sql
INSERT INTO public.hatedetect_authorized_users (user_id, role, active)
SELECT id, 'moderator', true
FROM auth.users
WHERE lower(email) = lower('CORREO_AUTORIZADO')
ON CONFLICT (user_id) DO UPDATE SET role='moderator', active=true;
```

Para revocar temporalmente el permiso:

```sql
UPDATE public.hatedetect_authorized_users
SET active=false
WHERE user_id=(SELECT id FROM auth.users WHERE lower(email)=lower('CORREO_A_REVOCAR'));
```

El correo se escribe únicamente en el SQL Editor de Supabase, **nunca en código, Git ni este chat**. Para autorizar evaluadores cambia el rol a `evaluator` pero ten en cuenta que la app pública no incluye todavía el módulo de anotación.

## 6. Limitaciones y próximos controles

Este cambio NO convierte la demostración en un panel completo de moderación. Sigue pendiente diseñar cola de comentarios, revisión humana, registro de decisiones, gestión segura de operadores y alertas/auditoría. La clasificación con comentarios sintéticos y métricas del corpus continúa siendo pública. Si se requiere proteger también el clasificador, se deberá usar un despliegue privado independiente o bloquearlo por completo.
