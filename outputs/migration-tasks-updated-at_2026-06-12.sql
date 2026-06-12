-- Optimistic versioning for auto-sequencing: detect concurrent edits before the
-- sequencer persists a day (two-coordinator guard). Trigger keeps it fresh on UPDATE.
ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE OR REPLACE FUNCTION public._touch_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_tasks_touch ON public.tasks;
CREATE TRIGGER trg_tasks_touch
  BEFORE UPDATE ON public.tasks
  FOR EACH ROW EXECUTE FUNCTION public._touch_updated_at();
