-- Migration: Add phlowtop monitoring schema
-- Version: 001
-- Description: Adds tables and functions for agent lifecycle monitoring

-- Check if migration has already been applied
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'phlow_tasks') THEN

        -- Extend existing agent_cards table
        ALTER TABLE agent_cards ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMPTZ DEFAULT NOW();
        ALTER TABLE agent_cards ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'IDLE'
            CHECK (status IN ('IDLE', 'WORKING', 'ERROR', 'OFFLINE'));
        ALTER TABLE agent_cards ADD COLUMN IF NOT EXISTS active_tasks INTEGER DEFAULT 0;

        -- Create phlow_tasks table
        CREATE TABLE phlow_tasks (
            task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id TEXT REFERENCES agent_cards(agent_id),
            client_agent_id TEXT,
            status TEXT DEFAULT 'SUBMITTED' CHECK (status IN ('SUBMITTED', 'WORKING', 'COMPLETED', 'FAILED')),
            task_type TEXT,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Create phlow_messages table
        CREATE TABLE phlow_messages (
            message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id UUID REFERENCES phlow_tasks(task_id) ON DELETE CASCADE,
            source_agent_id TEXT,
            target_agent_id TEXT,
            message_type TEXT,
            content JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        -- Create indexes
        CREATE INDEX idx_phlow_tasks_agent_id ON phlow_tasks(agent_id);
        CREATE INDEX idx_phlow_tasks_status ON phlow_tasks(status);
        CREATE INDEX idx_phlow_tasks_created_at ON phlow_tasks(created_at);
        CREATE INDEX idx_phlow_messages_task_id ON phlow_messages(task_id);
        CREATE INDEX idx_phlow_messages_created_at ON phlow_messages(created_at);

        -- Enable RLS
        ALTER TABLE phlow_tasks ENABLE ROW LEVEL SECURITY;
        ALTER TABLE phlow_messages ENABLE ROW LEVEL SECURITY;

        -- Create policies
        CREATE POLICY phlow_tasks_read ON phlow_tasks FOR SELECT USING (true);
        CREATE POLICY phlow_tasks_own ON phlow_tasks FOR ALL USING (
            agent_id = current_setting('phlow.agent_id', true)
            OR client_agent_id = current_setting('phlow.agent_id', true)
        );
        CREATE POLICY phlow_messages_read ON phlow_messages FOR SELECT USING (true);
        CREATE POLICY phlow_messages_write ON phlow_messages FOR INSERT WITH CHECK (
            source_agent_id = current_setting('phlow.agent_id', true)
            OR target_agent_id = current_setting('phlow.agent_id', true)
        );

        -- Create helper functions
        CREATE OR REPLACE FUNCTION increment_active_tasks(p_agent_id TEXT)
        RETURNS INTEGER AS $$
        DECLARE
            new_count INTEGER;
        BEGIN
            UPDATE agent_cards
            SET active_tasks = COALESCE(active_tasks, 0) + 1
            WHERE agent_id = p_agent_id
            RETURNING active_tasks INTO new_count;

            RETURN new_count;
        END;
        $$ LANGUAGE plpgsql;

        CREATE OR REPLACE FUNCTION decrement_active_tasks(p_agent_id TEXT)
        RETURNS INTEGER AS $$
        DECLARE
            new_count INTEGER;
        BEGIN
            UPDATE agent_cards
            SET active_tasks = GREATEST(COALESCE(active_tasks, 0) - 1, 0)
            WHERE agent_id = p_agent_id
            RETURNING active_tasks INTO new_count;

            RETURN new_count;
        END;
        $$ LANGUAGE plpgsql;

        -- Add trigger for updated_at
        CREATE TRIGGER update_phlow_tasks_updated_at
            BEFORE UPDATE ON phlow_tasks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();

        -- Create monitoring view
        CREATE OR REPLACE VIEW agent_monitoring_summary AS
        SELECT
            a.agent_id,
            a.name,
            a.status,
            a.active_tasks,
            a.last_heartbeat,
            a.service_url,
            COUNT(DISTINCT t.task_id) FILTER (WHERE t.status = 'COMPLETED' AND t.created_at > NOW() - INTERVAL '1 hour') as tasks_completed_1h,
            COUNT(DISTINCT t.task_id) FILTER (WHERE t.status = 'FAILED' AND t.created_at > NOW() - INTERVAL '1 hour') as tasks_failed_1h,
            COUNT(DISTINCT m.message_id) FILTER (WHERE m.created_at > NOW() - INTERVAL '1 minute') as messages_per_minute
        FROM agent_cards a
        LEFT JOIN phlow_tasks t ON a.agent_id = t.agent_id
        LEFT JOIN phlow_messages m ON (m.source_agent_id = a.agent_id OR m.target_agent_id = a.agent_id)
        GROUP BY a.agent_id, a.name, a.status, a.active_tasks, a.last_heartbeat, a.service_url;

        -- Grant access
        GRANT SELECT ON agent_monitoring_summary TO authenticated;

        RAISE NOTICE 'Phlowtop schema migration completed successfully';
    ELSE
        RAISE NOTICE 'Phlowtop schema already exists, skipping migration';
    END IF;
END $$;
