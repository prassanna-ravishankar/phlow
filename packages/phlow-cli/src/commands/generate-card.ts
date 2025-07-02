import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { createClient } from '@supabase/supabase-js';
import { ConfigManager } from '../utils/config';
import { SupabaseHelpers } from 'phlow-auth';
import fs from 'fs-extra';

export function createGenerateCardCommand(): Command {
  return new Command('generate-card')
    .description('Generate and register agent card with Supabase')
    .option('-o, --output <file>', 'Output file for agent card JSON')
    .option('--no-register', "Don't register with Supabase, just generate JSON")
    .action(async (options) => {
      const configManager = new ConfigManager();
      
      if (!(await configManager.exists())) {
        console.log(chalk.red('❌ No Phlow project found. Run `phlow init` first.'));
        return;
      }

      try {
        const config = await configManager.load();
        
        if (!config.agentCard) {
          console.log(chalk.red('❌ No agent card found in configuration.'));
          return;
        }

        const spinner = ora('Processing agent card...').start();

        // Create agent card JSON
        const agentCardJson = {
          ...config.agentCard,
          generatedAt: new Date().toISOString(),
          version: '1.0',
        };

        if (options.output) {
          await fs.writeJson(options.output, agentCardJson, { spaces: 2 });
          spinner.text = `Agent card saved to ${options.output}`;
        }

        if (options.register !== false) {
          if (!config.supabaseUrl || !config.supabaseAnonKey) {
            spinner.fail('❌ Supabase configuration missing');
            return;
          }

          spinner.text = 'Registering with Supabase...';
          
          const supabase = createClient(config.supabaseUrl, config.supabaseAnonKey);
          const helpers = new SupabaseHelpers(supabase);
          
          await helpers.registerAgentCard(config.agentCard);
          
          spinner.succeed('✅ Agent card registered successfully!');
        } else {
          spinner.succeed('✅ Agent card generated!');
        }

        console.log(chalk.green('\\n📋 Agent Card Details:'));
        console.log(chalk.gray(`   Agent ID: ${config.agentCard.agentId}`));
        console.log(chalk.gray(`   Name: ${config.agentCard.name}`));
        if (config.agentCard.description) {
          console.log(chalk.gray(`   Description: ${config.agentCard.description}`));
        }
        console.log(chalk.gray(`   Permissions: ${(config.agentCard.permissions || []).join(', ')}`));
        
        if (options.output) {
          console.log(chalk.blue(`\\n💾 Card saved to: ${options.output}`));
        }

      } catch (error: any) {
        console.error(chalk.red('❌ Failed to generate agent card:'), error.message);
        process.exit(1);
      }
    });
}