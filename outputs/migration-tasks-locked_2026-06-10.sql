-- Manual override flag: a locked task is pinned by the coordinator and the
-- auto-sequencer (Plan B) must never move, reorder, or gap-fill it.
ALTER TABLE public.tasks
  ADD COLUMN IF NOT EXISTS locked BOOLEAN NOT NULL DEFAULT false;
