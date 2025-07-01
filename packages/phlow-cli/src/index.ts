#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { createInitCommand } from './commands/init';
import { createGenerateCardCommand } from './commands/generate-card';
import { createDevStartCommand } from './commands/dev-start';
import { createTestTokenCommand } from './commands/test-token';

const program = new Command();

program
  .name('phlow')
  .description('CLI tools for Phlow - Agent-to-Agent authentication framework')
  .version('0.1.0');

// Add ASCII art banner
const banner = `
 ██████╗ ██╗  ██╗██╗      ██████╗ ██╗    ██╗
 ██╔══██╗██║  ██║██║     ██╔═══██╗██║    ██║
 ██████╔╝███████║██║     ██║   ██║██║ █╗ ██║
 ██╔═══╝ ██╔══██║██║     ██║   ██║██║███╗██║
 ██║     ██║  ██║███████╗╚██████╔╝╚███╔███╔╝
 ╚═╝     ╚═╝  ╚═╝╚══════╝ ╚═════╝  ╚══╝╚══╝ 
 
 Agent-to-Agent Authentication Framework
`;

program.addHelpText('beforeAll', chalk.blue(banner));

// Register commands
program.addCommand(createInitCommand());
program.addCommand(createGenerateCardCommand());
program.addCommand(createDevStartCommand());
program.addCommand(createTestTokenCommand());

// Add global error handler
process.on('unhandledRejection', (reason, promise) => {
  console.error(chalk.red('❌ Unhandled Rejection at:'), promise, chalk.red('reason:'), reason);
  process.exit(1);
});

process.on('uncaughtException', (error) => {
  console.error(chalk.red('❌ Uncaught Exception:'), error);
  process.exit(1);
});

// Parse and execute
program.parse(process.argv);

// Show help if no command provided
if (!process.argv.slice(2).length) {
  program.outputHelp();
}