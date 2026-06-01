-- Migration: duration_overrides on technicians
-- Date: 2026-06-01
-- Purpose: enables per-technician, per-category job duration overrides
--
-- Run in Supabase SQL Editor for the Maslul project.
-- Safe to run multiple times (IF NOT EXISTS).

ALTER TABLE technicians
  ADD COLUMN IF NOT EXISTS duration_overrides JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN technicians.duration_overrides IS
  'Per-category duration overrides for this technician. Format: { "cat_uuid": minutes }. '
  'If a category ID is present, its value overrides categories.duration_minutes for this tech only. '
  'Empty object = use category default for all job types.';
