# Slack-Claude Bot

A Slack bot that connects to Claude Code for interactive AI assistance. DM the bot or @mention it in channels to interact with Claude, with full conversation continuity and optional permission handling through Slack.

## Features

- **DM Support**: Send direct messages to the bot
- **@Mentions**: @mention the bot in any channel
- **Conversation Continuity**: Claude remembers the full conversation context within a thread (uses Claude SDK session resumption)
- **Interactive Permissions**: When Claude needs approval (file edits, bash commands), it asks in Slack and you reply to approve/deny
- **Threaded Responses**: All responses stay organized in threads
- **Session Commands**: Manual control with `/reset`, `/help`, `/status`
- **Single User Mode**: Restricts access to your Slack user ID only
- **Skills Support**: Auto-discovers and loads skills from your skills directory

## Prerequisites

1. **Claude Code CLI** installed and working
2. **Node.js 18+**
3. **Slack App** with Socket Mode enabled

## Setup

### 1. Create Slack App

Go to [api.slack.com/apps](https://api.slack.com/apps) and click "Create New App" > "From an app manifest".

Select your workspace, then paste this manifest:

```json
{
  "display_information": {
    "name": "Claude Assistant",
    "description": "AI assistant powered by Claude Code",
    "background_color": "#6B4E71"
  },
  "features": {
    "bot_user": {
      "display_name": "Claude",
      "always_online": true
    }
  },
  "oauth_config": {
    "scopes": {
      "bot": [
        "app_mentions:read",
        "chat:write",
        "im:history",
        "im:read",
        "im:write",
        "reactions:read",
        "reactions:write"
      ]
    }
  },
  "settings": {
    "event_subscriptions": {
      "bot_events": [
        "app_mention",
        "message.im"
      ]
    },
    "interactivity": {
      "is_enabled": false
    },
    "org_deploy_enabled": false,
    "socket_mode_enabled": true,
    "token_rotation_enabled": false
  }
}
```

After creating the app:

1. **Install to Workspace**: Go to "Install App" and click "Install to Workspace"
2. **Copy Bot Token**: After install, copy the "Bot User OAuth Token" (starts with `xoxb-`)
3. **Create App Token**: Go to "Basic Information" > "App-Level Tokens" > "Generate Token and Scopes"
   - Name: `socket-mode`
   - Scope: `connections:write`
   - Copy the token (starts with `xapp-`)

### 2. Install Dependencies

```bash
cd .claude/plugins/slack-claude
npm install
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your values:

```bash
# Required - from Slack app setup above
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# Recommended: Your Slack user ID (find it in Slack profile > ... menu > Copy member ID)
SLACK_ALLOWED_USER=U12345678

# Working directory (where your code/projects live)
CLAUDE_WORKING_DIR=/path/to/your/workspace

# Skills directory (defaults to ~/.claude/skills)
# CLAUDE_SKILLS_DIR=/path/to/.claude/skills

# Enable interactive permissions (require approval for write tools)
# When false (default), Claude runs with --dangerously-skip-permissions
# When true, Claude asks for approval in Slack for Bash, Write, Edit tools
# CLAUDE_REQUIRE_PERMISSIONS=true

# Session timeout in milliseconds (default: 0 = never timeout)
# Sessions persist until manually cleared with /reset
# CLAUDE_SESSION_TIMEOUT_MS=0

# Debug logging
# DEBUG=true
```

### 4. Start the Bot

**Quick start (for testing):**
```bash
npm start
```

**Recommended: Run with PM2 (persistent, auto-restart):**
```bash
# Install PM2 globally (one time)
npm install -g pm2

# Start the bot with PM2
pm2 start index.js --name "slack-claude"

# Make it auto-start on system boot
pm2 startup
pm2 save
```

You should see:
```
[BOT] Slack Bolt app starting...
[BOT] Bot is running! Listening for messages...
```

**PM2 Commands:**
| Command | Description |
|---------|-------------|
| `pm2 status` | Check if bot is running |
| `pm2 logs slack-claude` | View live logs |
| `pm2 logs slack-claude --lines 100` | View last 100 log lines |
| `pm2 restart slack-claude` | Restart the bot |
| `pm2 stop slack-claude` | Stop the bot |
| `pm2 delete slack-claude` | Remove from PM2 |

## Usage

### Direct Messages

Just DM the bot:
```
You: What's in the package.json file?
Bot: [Claude's response with file contents]

You: Can you also check the README?
Bot: [Claude remembers context and responds about README]
```

### @Mentions

Mention the bot in any channel (the bot must be invited to the channel):
```
You: @Claude list all TODO comments in the src folder
Bot: [Claude's response]
```

### Bot Commands

You can use these commands anytime:

| Command | Description |
|---------|-------------|
| `/reset`, `/new`, `/clear`, `/forget` | Clear current session and start fresh |
| `/help`, `help`, `commands` | Show available commands |
| `/status`, `status`, `/session` | Show current session info |

Commands work naturally in conversation:
- "can you /reset" ✓
- "/reset the session" ✓
- "please reset" ✓

### Conversation Continuity

The bot maintains conversation context within each thread:

```
You: What files are in the src directory?
Bot: [Lists files including api.js, utils.js, etc.]

You: Tell me about the first one
Bot: [Claude remembers and describes api.js]

You: /reset
Bot: Session cleared. Starting fresh.

You: Tell me about the first one
Bot: I don't have context about what you're referring to...
```

### Permission Handling

When `CLAUDE_REQUIRE_PERMISSIONS=true`, Claude asks before write operations:

```
You: Fix the bug in api.js

Bot: 🔐 Claude wants to: *Edit*
     File: `src/api.js`
     ```
     const response = await fetch(url, { timeout: 5000 });
     ```

     Reply with:
     • `yes` or `y` to approve
     • `no` or `n` to deny
     • Or additional instructions

You: yes

Bot: [Claude proceeds with the edit and shows result]
```

You can provide additional context:
```
You: yes, but also add error handling
```

## How It Works

1. You send a message to the bot (DM or @mention)
2. Bot uses the Claude SDK `query()` API to process your message
3. Claude runs in the configured working directory (with all your settings.json permissions)
4. For follow-up messages in the same thread, the bot resumes the same Claude session
5. When Claude needs permission (if enabled), it posts to Slack and waits for your reply
6. Your reply is sent back to Claude as the approval/denial
7. Sessions persist until manually cleared with `/reset`

### Session Architecture

```
Thread A (ts: 123.456)          Thread B (ts: 789.012)
├── Message 1 → New session     ├── Message 1 → New session
├── Message 2 → Resume session  ├── Message 2 → Resume session
├── /reset → Clear              └── Message 3 → Resume session
└── Message 3 → New session
```

Each Slack thread maintains its own Claude session. The Claude SDK's session resumption feature keeps full conversation context.

## Configuration Options

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_BOT_TOKEN` | Yes | - | Bot OAuth token (xoxb-...) |
| `SLACK_APP_TOKEN` | Yes | - | App-level token (xapp-...) |
| `SLACK_ALLOWED_USER` | No | - | Restrict to this user ID |
| `CLAUDE_WORKING_DIR` | No | cwd | Working directory for Claude |
| `CLAUDE_SKILLS_DIR` | No | ~/.claude/skills | Directory containing Claude skills |
| `CLAUDE_REQUIRE_PERMISSIONS` | No | false | Require Slack approval for write tools |
| `CLAUDE_COMMAND` | No | `claude` | Claude CLI command |
| `CLAUDE_SESSION_TIMEOUT_MS` | No | 0 | Session timeout (0 = never) |
| `DEBUG` | No | false | Enable debug logging |

## File Structure

```
.claude/plugins/slack-claude/
├── index.js              # Entry point
├── config.js             # Environment config
├── package.json          # Dependencies
├── src/
│   ├── bot.js            # Slack Bolt app, message handling, commands
│   ├── claude-runner.js  # Claude SDK query() with session resumption
│   ├── permission-parser.js  # Parses permission prompts (legacy)
│   └── session-manager.js    # Tracks sessions per thread
├── .env.example          # Config template
└── README.md             # This file
```

## Troubleshooting

### Bot doesn't respond

1. Check bot is running: `npm start`
2. Verify tokens in `.env` are correct
3. For @mentions: ensure bot is invited to the channel (`/invite @Claude`)
4. Check `SLACK_ALLOWED_USER` matches your user ID
5. Check console for errors

### Bot says "A conversation is already in progress"

The previous request is still running. Wait for it to complete or use `/reset` to clear the session.

### Bot doesn't remember previous messages

Make sure you're replying in the **same thread**. New top-level messages start new sessions. Use `/status` to check session state.

### Permission requests timeout

Permission requests timeout after 55 seconds. Reply faster or adjust your workflow.

### "Session cleared" but bot still remembers

The Claude SDK session was cleared, but Slack's thread continues. Start a new thread for a completely fresh start.

## Security Notes

- **Always set `SLACK_ALLOWED_USER`** to restrict access to your user ID only
- Claude runs with your local permissions (can access your files)
- The bot loads your `~/.claude/settings.json` permissions automatically
- When `CLAUDE_REQUIRE_PERMISSIONS=false` (default), Claude bypasses all permission prompts
- Sessions persist indefinitely by default - use `/reset` to clear sensitive context

## Advanced: Skills Integration

The bot auto-discovers skills from `CLAUDE_SKILLS_DIR` (default: `~/.claude/skills/`).

Each skill folder with a `SKILL.md` file is loaded as a plugin. Skills with a `server.sh` are registered as MCP servers.

```
~/.claude/skills/
├── pr-reviewer/
│   ├── SKILL.md          # Skill definition
│   └── scripts/          # Skill scripts
├── prd/
│   ├── SKILL.md
│   └── server.sh         # MCP server (optional)
```
