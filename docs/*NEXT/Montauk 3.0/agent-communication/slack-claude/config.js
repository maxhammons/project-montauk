const path = require('path');

// Load environment variables from .env if it exists
try {
  require('dotenv').config({ path: path.join(__dirname, '.env') });
} catch (e) {
  // dotenv not installed, rely on environment variables
}

const config = {
  // Slack credentials
  slack: {
    botToken: process.env.SLACK_BOT_TOKEN,
    appToken: process.env.SLACK_APP_TOKEN,
    signingSecret: process.env.SLACK_SIGNING_SECRET,
  },

  // Access control
  allowedUserId: process.env.SLACK_ALLOWED_USER || null,

  // Claude configuration
  claude: {
    workingDir: process.env.CLAUDE_WORKING_DIR || process.cwd(),
    command: process.env.CLAUDE_COMMAND || 'claude',
    sessionTimeoutMs: parseInt(process.env.CLAUDE_SESSION_TIMEOUT_MS, 10) || 0, // 0 = no timeout (sessions persist)
    // If true, require Slack approval for write operations (Bash, Write, Edit)
    // If false, bypass all permissions (dangerous but convenient)
    requirePermissions: process.env.CLAUDE_REQUIRE_PERMISSIONS === 'true',
    // Path to skills directory (for plugins/MCP servers)
    skillsDir: process.env.CLAUDE_SKILLS_DIR || path.join(process.env.HOME || '', '.claude', 'skills'),
  },

  // Debug
  debug: process.env.DEBUG === 'true',
};

// Validate required config
function validateConfig() {
  const missing = [];

  if (!config.slack.botToken) missing.push('SLACK_BOT_TOKEN');
  if (!config.slack.appToken) missing.push('SLACK_APP_TOKEN');

  if (missing.length > 0) {
    console.error('Missing required environment variables:', missing.join(', '));
    console.error('Copy .env.example to .env and fill in the values.');
    process.exit(1);
  }
}

module.exports = { config, validateConfig };
