-- Reset all PureWater seeded tasks to pending so the coordinator can re-dispatch them
-- under the new scheduling rules (service windows, far-to-near, slot release).
--
-- Run ONCE after deploying the scheduling overhaul.
-- Tasks retain their city and category — only assignment fields are cleared.
--
-- Affects tenant: 00000000-0000-0000-0000-000000000001 (PureWater Israel)

UPDATE public.tasks
SET
  status                 = 'pending',
  technician_id          = NULL,
  scheduled_date         = NULL,
  scheduled_time         = NULL,
  scheduled_window_start = NULL,
  scheduled_window_end   = NULL,
  assign_id              = NULL,
  lat                    = NULL,
  lon                    = NULL,
  geocoded_at            = NULL
WHERE
  tenant_id = '00000000-0000-0000-0000-000000000001'
  AND status IN ('assigned', 'pending');

-- Verify
SELECT COUNT(*) AS reset_count FROM public.tasks
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
  AND status = 'pending';
