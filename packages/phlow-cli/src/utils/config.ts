import fs from 'fs-extra';
import path from 'path';
import { AgentCard } from 'phlow-auth';

export interface PhlowCliConfig {
  supabaseUrl?: string;
  supabaseAnonKey?: string;
  agentCard?: AgentCard;
  privateKey?: string;
}

export class ConfigManager {
  private configPath: string;

  constructor(configPath?: string) {
    this.configPath = configPath || path.join(process.cwd(), '.phlow.json');
  }

  async load(): Promise<PhlowCliConfig> {
    try {
      if (await fs.pathExists(this.configPath)) {
        return await fs.readJson(this.configPath);
      }
      return {};
    } catch (error) {
      console.error('Error loading config:', error);
      return {};
    }
  }

  async save(config: PhlowCliConfig): Promise<void> {
    try {
      await fs.writeJson(this.configPath, config, { spaces: 2 });
    } catch (error) {
      console.error('Error saving config:', error);
      throw error;
    }
  }

  async update(updates: Partial<PhlowCliConfig>): Promise<void> {
    const config = await this.load();
    const updatedConfig = { ...config, ...updates };
    await this.save(updatedConfig);
  }

  async exists(): Promise<boolean> {
    return fs.pathExists(this.configPath);
  }

  getConfigPath(): string {
    return this.configPath;
  }
}