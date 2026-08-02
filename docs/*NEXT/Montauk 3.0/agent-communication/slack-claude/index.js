#!/usr/bin/env node

/**
 * Slack-Claude Bot
 *
 * A Slack bot that connects to Claude Code for interactive AI assistance.
 * Supports DMs and @mentions with interactive permission handling.
 *
 * Usage:
 *   npm start
 *   # or
 *   node index.js
 */

const { config, validateConfig } = require('./config');
const { createApp } = require('./src/bot');

async function main() {
  // Validate required config
  validateConfig();

  console.log('Starting Slack-Claude bot...');
  console.log(`Working directory: ${config.claude.workingDir}`);
  console.log(`Claude command: ${config.claude.command}`);

  if (config.allowedUserId) {
    console.log(`Restricted to user: ${config.allowedUserId}`);
  } else {
    console.log('Warning: No user restriction set (SLACK_ALLOWED_USER)');
  }

  // Create and start the app
  const app = createApp();

  await app.start();

  console.log('Bot is running! Listening for messages...');
  console.log('Press Ctrl+C to stop.');
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down...');
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\nShutting down...');
  process.exit(0);
});

// Run
main().catch((err) => {
  console.error('Failed to start bot:', err);
  process.exit(1);
});
