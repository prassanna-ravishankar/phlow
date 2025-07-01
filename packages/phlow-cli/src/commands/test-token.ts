import { Command } from 'commander';
import chalk from 'chalk';
import { ConfigManager } from '../utils/config';
import { generateToken } from 'phlow-auth';
import jwt from 'jsonwebtoken';

export function createTestTokenCommand(): Command {
  return new Command('test-token')
    .description('Generate a test token for authentication')
    .option('-t, --target <agentId>', 'Target agent ID', 'test-agent')
    .option('-e, --expires <duration>', 'Token expiration (e.g., 1h, 30m)', '1h')
    .option('--decode', 'Decode and display an existing token')
    .argument('[token]', 'Token to decode (when using --decode)')
    .action(async (token, options) => {
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

        if (options.decode) {
          if (!token) {
            console.log(chalk.red('❌ Token required when using --decode option.'));
            return;
          }

          const decoded = jwt.decode(token);
          
          if (!decoded) {
            console.log(chalk.red('❌ Invalid token format.'));
            return;
          }

          console.log(chalk.green('🔍 Token Details:'));
          console.log(chalk.gray(JSON.stringify(decoded, null, 2)));
          return;
        }

        const testToken = generateToken(
          config.agentCard,
          config.privateKey,
          options.target,
          options.expires
        );

        console.log(chalk.green('🎫 Test token generated!'));
        console.log(chalk.blue('\\nToken:'));
        console.log(chalk.gray(testToken));
        
        console.log(chalk.blue('\\nUsage:'));
        console.log(chalk.gray('curl -H "Authorization: Bearer ' + testToken + '" \\\\'));
        console.log(chalk.gray('     -H "X-Phlow-Agent-Id: ' + config.agentCard.agentId + '" \\\\'));
        console.log(chalk.gray('     http://localhost:3000/protected'));

        console.log(chalk.blue('\\nToken Details:'));
        console.log(chalk.gray(`  Issuer: ${config.agentCard.agentId}`));
        console.log(chalk.gray(`  Audience: ${options.target}`));
        console.log(chalk.gray(`  Expires: ${options.expires}`));
        console.log(chalk.gray(`  Permissions: ${config.agentCard.permissions.join(', ')}`));

      } catch (error: any) {
        console.error(chalk.red('❌ Failed to generate test token:'), error.message);
        process.exit(1);
      }
    });
}