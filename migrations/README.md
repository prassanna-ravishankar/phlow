# Phlow Database Migrations

This directory contains SQL migration scripts for the Phlow database schema.

## Running Migrations

To apply migrations to your Supabase database:

1. **Via Supabase Dashboard:**
   - Go to SQL Editor in your Supabase dashboard
   - Copy and paste the migration file contents
   - Run the query

2. **Via psql:**
   ```bash
   psql -h your-project.supabase.co -p 5432 -U postgres -d postgres -f migrations/001_add_phlowtop_schema.sql
   ```

3. **Via Supabase CLI:**
   ```bash
   supabase db push --file migrations/001_add_phlowtop_schema.sql
   ```

## Migration Files

- `001_add_phlowtop_schema.sql` - Adds monitoring tables and functions for phlowtop:
  - Extends `agent_cards` with status tracking
  - Adds `phlow_tasks` table for task lifecycle
  - Adds `phlow_messages` table for inter-agent communication
  - Creates helper functions for task counting
  - Creates `agent_monitoring_summary` view

## Notes

- Migrations are idempotent - they check if changes have already been applied
- The realtime publication requires SUPERUSER privileges and may need to be run separately
- All new tables have Row Level Security (RLS) enabled with appropriate policies
