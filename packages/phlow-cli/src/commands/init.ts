import { Command } from 'commander';
import inquirer from 'inquirer';
import chalk from 'chalk';
import ora from 'ora';
import { ConfigManager } from '../utils/config';
import { generateKeyPair } from '../utils/crypto';
import { AgentCard } from 'phlow-auth';

export function createInitCommand(): Command {
  return new Command('init')
    .description('Initialize a new Phlow project')
    .option('-f, --force', 'Overwrite existing configuration')
    .action(async (options) => {
      const configManager = new ConfigManager();
      
      if (await configManager.exists() && !options.force) {
        console.log(chalk.red('⚠️  Phlow project already initialized. Use --force to overwrite.'));
        return;
      }

      console.log(chalk.blue('🚀 Initializing Phlow project...\\n'));

      try {
        const answers = await inquirer.prompt([
          {
            type: 'input',
            name: 'supabaseUrl',
            message: 'Supabase URL:',
            validate: (input) => input.trim() !== '' || 'Supabase URL is required',
          },
          {
            type: 'password',
            name: 'supabaseAnonKey',
            message: 'Supabase Anon Key:',
            mask: '*',
            validate: (input) => input.trim() !== '' || 'Supabase Anon Key is required',
          },
          {
            type: 'input',
            name: 'agentId',
            message: 'Agent ID:',
            validate: (input) => {
              const trimmed = input.trim();
              if (trimmed === '') return 'Agent ID is required';
              if (!/^[a-zA-Z0-9_-]+$/.test(trimmed)) {
                return 'Agent ID can only contain letters, numbers, hyphens, and underscores';
              }
              return true;
            },
          },
          {
            type: 'input',
            name: 'agentName',
            message: 'Agent Name:',
            validate: (input) => input.trim() !== '' || 'Agent Name is required',
          },
          {
            type: 'input',
            name: 'agentDescription',
            message: 'Agent Description (optional):',
          },
          {
            type: 'checkbox',
            name: 'permissions',
            message: 'Select permissions:',
            choices: [
              { name: 'read:data', value: 'read:data' },
              { name: 'write:data', value: 'write:data' },
              { name: 'admin:users', value: 'admin:users' },
              { name: 'manage:agents', value: 'manage:agents' },
              { name: 'audit:logs', value: 'audit:logs' },
            ],
          },
          {
            type: 'confirm',
            name: 'generateKeys',
            message: 'Generate new RSA key pair?',
            default: true,
          },
        ]);

        const spinner = ora('Generating configuration...').start();

        let publicKey = '';
        let privateKey = '';

        if (answers.generateKeys) {
          spinner.text = 'Generating RSA key pair...';
          const keyPair = generateKeyPair();
          publicKey = keyPair.publicKey;
          privateKey = keyPair.privateKey;
        }

        const agentCard: AgentCard = {
          agentId: answers.agentId,
          name: answers.agentName,
          description: answers.agentDescription || undefined,
          permissions: answers.permissions,
          publicKey,
        };

        const config = {
          supabaseUrl: answers.supabaseUrl,
          supabaseAnonKey: answers.supabaseAnonKey,
          agentCard,
          privateKey,
        };

        spinner.text = 'Saving configuration...';
        await configManager.save(config);

        spinner.succeed('Project initialized successfully!');

        console.log(chalk.green('\\n✅ Phlow project initialized!'));
        console.log(chalk.gray(`   Config saved to: ${configManager.getConfigPath()}`));
        
        if (answers.generateKeys) {
          console.log(chalk.yellow('\\n🔐 Keep your private key secure and never commit it to version control!'));
        }
        
        console.log(chalk.blue('\\n📖 Next steps:'));
        console.log(chalk.gray('   • Run `phlow generate-card` to register your agent'));
        console.log(chalk.gray('   • Use `phlow dev-start` to start local development'));

      } catch (error: any) {
        console.error(chalk.red('❌ Failed to initialize project:'), error.message);
        process.exit(1);
      }
    });
}