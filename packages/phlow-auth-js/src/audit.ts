import { SupabaseClient } from '@supabase/supabase-js';
import { AuditLog } from './types';

export class AuditLogger {
  private supabase: SupabaseClient;
  private queue: AuditLog[] = [];
  private flushInterval: NodeJS.Timeout;
  private maxBatchSize = 100;

  constructor(supabase: SupabaseClient, flushIntervalMs: number = 5000) {
    this.supabase = supabase;
    this.flushInterval = setInterval(() => this.flush(), flushIntervalMs);
  }

  async log(entry: AuditLog): Promise<void> {
    this.queue.push(entry);
    
    if (this.queue.length >= this.maxBatchSize) {
      await this.flush();
    }
  }

  private async flush(): Promise<void> {
    if (this.queue.length === 0) {
      return;
    }

    const entries = this.queue.splice(0, this.maxBatchSize);
    
    try {
      const { error } = await this.supabase
        .from('phlow_audit_logs')
        .insert(
          entries.map(entry => ({
            timestamp: entry.timestamp.toISOString(),
            event: entry.event,
            agent_id: entry.agentId,
            target_agent_id: entry.targetAgentId,
            details: entry.details,
          }))
        );

      if (error) {
        console.error('Failed to insert audit logs:', error);
        this.queue.unshift(...entries);
      }
    } catch (error) {
      console.error('Error flushing audit logs:', error);
      this.queue.unshift(...entries);
    }
  }

  async close(): Promise<void> {
    clearInterval(this.flushInterval);
    await this.flush();
  }
}