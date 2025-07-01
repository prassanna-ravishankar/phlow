import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import path from 'path';
import fs from 'fs-extra';
import { ConfigManager } from '../utils/config';
import { 
  writeTemplate, 
  BASIC_AGENT_TEMPLATE, 
  ENV_TEMPLATE, 
  PACKAGE_JSON_TEMPLATE,
  SUPABASE_SCHEMA 
} from '../utils/templates';

export function createDevStartCommand(): Command {
  return new Command('dev-start')
    .description('Start local development environment')
    .option('-p, --port <port>', 'Port for the development server', '3000')
    .option('-d, --dir <directory>', 'Directory to create dev project', './phlow-dev-agent')
    .action(async (options) => {
      const configManager = new ConfigManager();
      
      if (!(await configManager.exists())) {
        console.log(chalk.red('❌ No Phlow project found. Run `phlow init` first.'));
        return;
      }

      try {
        const config = await configManager.load();
        
        if (!config.agentCard || !config.privateKey) {
          console.log(chalk.red('❌ Agent configuration incomplete.'));
          return;
        }

        const spinner = ora('Setting up development environment...').start();
        const devDir = path.resolve(options.dir);

        // Create development directory
        await fs.ensureDir(devDir);

        // Generate package.json
        spinner.text = 'Creating package.json...';
        await writeTemplate(
          path.join(devDir, 'package.json'),
          PACKAGE_JSON_TEMPLATE,
          {
            PACKAGE_NAME: `${config.agentCard.agentId}-dev`,
          }
        );

        // Generate main agent file
        spinner.text = 'Creating agent server...';
        await writeTemplate(
          path.join(devDir, 'index.js'),
          BASIC_AGENT_TEMPLATE,
          {
            AGENT_ID: config.agentCard.agentId,
            AGENT_NAME: config.agentCard.name,
            AGENT_DESCRIPTION: config.agentCard.description || 'Development agent',
            AGENT_PERMISSIONS: JSON.stringify(config.agentCard.permissions),
          }
        );

        // Generate .env file
        spinner.text = 'Creating environment file...';
        await writeTemplate(
          path.join(devDir, '.env'),
          ENV_TEMPLATE,
          {
            SUPABASE_URL: config.supabaseUrl || '',
            SUPABASE_ANON_KEY: config.supabaseAnonKey || '',
            AGENT_PUBLIC_KEY: config.agentCard.publicKey.replace(/\\n/g, '\\\\n'),
            AGENT_PRIVATE_KEY: config.privateKey.replace(/\\n/g, '\\\\n'),
          }
        );

        // Create Supabase schema file
        spinner.text = 'Creating database schema...';
        await fs.writeFile(
          path.join(devDir, 'supabase-schema.sql'),
          SUPABASE_SCHEMA
        );

        // Create .gitignore
        await fs.writeFile(
          path.join(devDir, '.gitignore'),
          `node_modules/
.env
.env.local
*.log
dist/
build/
`
        );

        // Create README
        spinner.text = 'Creating documentation...';
        const readme = `# ${config.agentCard.name} - Development Agent

This is a development setup for your Phlow agent.

## Getting Started

1. Install dependencies:
   \\`\\`\\`bash
   npm install
   \\`\\`\\`

2. Set up your Supabase database:
   - Run the SQL in \`supabase-schema.sql\` in your Supabase SQL editor
   - Update the \`.env\` file with your Supabase credentials

3. Start the development server:
   \\`\\`\\`bash
   npm run dev
   \\`\\`\\`

## Endpoints

- \`GET /health\` - Health check
- \`GET /protected\` - Protected endpoint requiring authentication

## Testing Authentication

Use the Phlow CLI to test authentication:

\\`\\`\\`bash
# Generate a test token
phlow test-token --target ${config.agentCard.agentId}

# Test the protected endpoint
curl -H "Authorization: Bearer <token>" \\
     -H "X-Phlow-Agent-Id: <your-agent-id>" \\
     http://localhost:${options.port}/protected
\\`\\`\\`

## Agent Details

- **Agent ID**: ${config.agentCard.agentId}
- **Name**: ${config.agentCard.name}
- **Permissions**: ${config.agentCard.permissions.join(', ')}
`;

        await fs.writeFile(path.join(devDir, 'README.md'), readme);

        spinner.succeed('✅ Development environment created!');

        console.log(chalk.green('\\n🚀 Development environment ready!'));
        console.log(chalk.gray(`   Location: ${devDir}`));
        console.log(chalk.blue('\\n📖 Next steps:'));
        console.log(chalk.gray(`   1. cd ${options.dir}`));
        console.log(chalk.gray('   2. npm install'));
        console.log(chalk.gray('   3. Update .env with your Supabase credentials'));
        console.log(chalk.gray('   4. Run the SQL schema in your Supabase project'));
        console.log(chalk.gray('   5. npm run dev'));
        console.log(chalk.yellow(`\\n🌐 Your agent will be available at: http://localhost:${options.port}`));

      } catch (error: any) {
        console.error(chalk.red('❌ Failed to create development environment:'), error.message);
        process.exit(1);
      }
    });
}