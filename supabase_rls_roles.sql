-- PASO FINAL: aplicar SOLO después de probar el código de la rama.
-- Requiere public.hatedetect_authorized_users con admin activo y RLS.
-- Sigue manteniendo cada Historial separado por dueño.
BEGIN;

DROP POLICY IF EXISTS hatedetect_history_select_own ON public.hatedetect_history;
DROP POLICY IF EXISTS hatedetect_history_insert_own ON public.hatedetect_history;
DROP POLICY IF EXISTS hatedetect_history_delete_own ON public.hatedetect_history;

CREATE POLICY hatedetect_history_select_own
ON public.hatedetect_history FOR SELECT TO authenticated
USING (
  user_id = (select auth.uid())
  AND EXISTS (
    SELECT 1 FROM public.hatedetect_authorized_users a
    WHERE a.user_id = (select auth.uid())
      AND a.active IS TRUE
      AND a.role IN ('admin', 'moderator')
  )
);

CREATE POLICY hatedetect_history_insert_own
ON public.hatedetect_history FOR INSERT TO authenticated
WITH CHECK (
  user_id = (select auth.uid())
  AND EXISTS (
    SELECT 1 FROM public.hatedetect_authorized_users a
    WHERE a.user_id = (select auth.uid())
      AND a.active IS TRUE
      AND a.role IN ('admin', 'moderator')
  )
);

CREATE POLICY hatedetect_history_delete_own
ON public.hatedetect_history FOR DELETE TO authenticated
USING (
  user_id = (select auth.uid())
  AND EXISTS (
    SELECT 1 FROM public.hatedetect_authorized_users a
    WHERE a.user_id = (select auth.uid())
      AND a.active IS TRUE
      AND a.role IN ('admin', 'moderator')
  )
);

COMMIT;
