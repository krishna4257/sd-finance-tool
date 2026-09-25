-- Optional SQL migration script
-- As requested, 0 DB changes are executed automatically.
-- Photos are stored on the filesystem in static/uploads/employees/<eid>.<ext>.
-- If desired in the future, run:
ALTER TABLE employee ADD COLUMN IF NOT EXISTS photo_url TEXT;
