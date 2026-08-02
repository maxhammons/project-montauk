/**
 * Slack Bot - Main bot logic using Bolt framework
 *
 * Handles:
 * - Direct messages to the bot
 * - @mentions in channels
 * - Permission approval flow through thread replies
 */

const { App } = require('@slack/bolt');
const fs = require('fs');
const path = require('path');
const { config } = require('../config');
const SessionManager = require('./session-manager');
const {
  runClaudeStreaming,
  setPermissionCallback,
  handlePermissionResponse,
  hasPendingPermission,
} = require('./claude-runner');

// Initialize session manager
const sessions = new SessionManager(config.claude.sessionTimeoutMs);

/**
 * Create and configure the Slack Bolt app
 * @returns {App}
 */
function createApp() {
  const app = new App({
    token: config.slack.botToken,
    appToken: config.slack.appToken,
    socketMode: true,
    // signingSecret only needed for HTTP mode
  });

  // Store the Slack client for permission callbacks
  let slackClient = null;

  // Set up permission callback to post to Slack
  setPermissionCallback(async (threadKey, toolName, formattedInput) => {
    if (!slackClient) {
      throw new Error('Slack client not initialized');
    }

    // Parse threadKey to get channel and thread_ts
    const [channel, threadTs] = threadKey.split(':');

    await slackClient.chat.postMessage({
      channel,
      thread_ts: threadTs,
      text: `🔐 *Permission Required: ${toolName}*\n\n${formattedInput}\n\n_Reply with *yes* to approve or *no* to deny (55s timeout)_`,
    });
  });

  // Debug: log all events
  app.use(async ({ event, next, client }) => {
    // Store client reference for permission callbacks
    if (!slackClient) {
      slackClient = client;
    }
    console.log('[DEBUG] Event received:', event?.type, event?.subtype || '');
    await next();
  });

  // Handle direct messages
  app.message(async ({ message, say, client }) => {
    console.log('[BOT] Received message:', message.text?.substring(0, 50));

    // Ignore bot messages and message changes
    if (message.subtype || message.bot_id) {
      console.log('[BOT] Ignoring bot/subtype message');
      return;
    }

    // Check if user is allowed
    if (config.allowedUserId && message.user !== config.allowedUserId) {
      await say("This bot is configured for a specific user only.");
      return;
    }

    // Extract text from voice messages (Slack audio clips with transcription)
    let promptText = message.text;
    if (message.files) {
      for (const file of message.files) {
        if (file.subtype === 'slack_audio' && file.transcription?.text) {
          console.log('[BOT] Voice message detected, using transcription');
          promptText = file.transcription.text;
          break;
        }
      }
    }

    // Use thread_ts as session key - each thread is its own Claude session
    // If no thread_ts, this is a new conversation - use message.ts as the thread root
    const threadTs = message.thread_ts || message.ts;
    const sessionKey = `${message.channel}:${threadTs}`;

    // Handle bot commands (check if message starts with or is exactly a command)
    const commandMatch = promptText?.trim().toLowerCase();
    const resetCommands = ['/reset', '/new', '/clear', '/forget', 'reset', 'new session', 'start fresh', 'clear session'];
    const isResetCommand = resetCommands.some(cmd => commandMatch === cmd || commandMatch.startsWith(cmd + ' ') || commandMatch.endsWith(' ' + cmd));
    if (isResetCommand) {
      const existingSession = sessions.get(sessionKey);
      if (existingSession) {
        sessions.complete(sessionKey); // Remove the session
        console.log('[BOT] Session cleared by user command:', commandMatch);
        await say({
          text: '🔄 Session cleared. Starting fresh - I no longer remember our previous conversation in this thread.',
          thread_ts: threadTs,
        });
      } else {
        await say({
          text: "No active session to clear. You're already starting fresh!",
          thread_ts: threadTs,
        });
      }
      return;
    }

    // Handle help command
    const helpCommands = ['/help', 'help', 'commands', '/commands'];
    if (helpCommands.some(cmd => commandMatch === cmd)) {
      await say({
        text: `*Available Commands:*
• \`/reset\` or \`/new\` or \`/clear\` or \`/forget\` - Clear session and start fresh
• \`/help\` - Show this help message
• \`/status\` - Show current session status

Just send a message to chat with Claude. Follow-up messages in the same thread will continue the conversation.`,
        thread_ts: threadTs,
      });
      return;
    }

    // Handle status command
    const statusCommands = ['/status', 'status', '/session', 'session status'];
    if (statusCommands.some(cmd => commandMatch === cmd)) {
      const existingSession = sessions.get(sessionKey);
      if (existingSession) {
        const age = Math.round((Date.now() - existingSession.createdAt) / 1000 / 60);
        await say({
          text: `*Session Status:*
• State: ${existingSession.state}
• Age: ${age} minutes
• Has Claude session ID: ${existingSession.claudeSessionId ? 'Yes (can resume)' : 'No'}`,
          thread_ts: threadTs,
        });
      } else {
        await say({
          text: 'No active session in this thread. Send a message to start one!',
          thread_ts: threadTs,
        });
      }
      return;
    }

    // Check if this is a response to a pending permission request
    if (hasPendingPermission(sessionKey)) {
      console.log('[BOT] Handling permission response:', promptText);
      const handled = handlePermissionResponse(sessionKey, promptText);
      if (handled) {
        // Permission was handled, don't process as new prompt
        return;
      }
    }

    // Check if session exists
    const existingSession = sessions.get(sessionKey);
    if (existingSession) {
      // Check if there's a pending permission (user might be responding)
      if (hasPendingPermission(sessionKey)) {
        console.log('[BOT] Session active with pending permission, message handled above');
        return;
      }

      // If session is idle, this is a follow-up message - resume the conversation
      if (sessions.isIdle(sessionKey)) {
        console.log('[BOT] Resuming idle session for follow-up message');
        const resumeSessionId = sessions.getClaudeSessionId(sessionKey);
        sessions.setRunning(sessionKey);

        await runClaudeSession({
          prompt: promptText,
          sessionKey,
          channel: message.channel,
          threadTs,
          say,
          client,
          resumeSessionId, // Resume previous conversation
        });
        return;
      }

      // Session is running, tell user to wait
      await say({
        text: "I'm still processing your previous request. Please wait.",
        thread_ts: threadTs,
      });
      return;
    }

    console.log('[BOT] Starting new Claude session for thread:', threadTs);

    // Start new Claude session
    await runClaudeSession({
      prompt: promptText,
      sessionKey,
      channel: message.channel,
      threadTs,
      say,
      client,
      resumeSessionId: null, // New session
    });
  });

  // Handle @mentions in channels
  app.event('app_mention', async ({ event, say, client }) => {
    // Check if user is allowed
    if (config.allowedUserId && event.user !== config.allowedUserId) {
      await say({
        text: "This bot is configured for a specific user only.",
        thread_ts: event.ts,
      });
      return;
    }

    const sessionKey = event.thread_ts || event.ts;

    // Remove the @mention from the text
    const text = event.text.replace(/<@[A-Z0-9]+>/g, '').trim();

    if (!text) {
      await say({
        text: "Hi! Send me a message and I'll process it with Claude.",
        thread_ts: sessionKey,
      });
      return;
    }

    // Check for existing session
    if (sessions.get(sessionKey)) {
      await say({
        text: "I'm still processing a request in this thread. Please wait.",
        thread_ts: sessionKey,
      });
      return;
    }

    // Start Claude session (skip reactions to reduce Activity feed noise)
    await runClaudeSession({
      prompt: text,
      sessionKey,
      channel: event.channel,
      say,
      client,
    });
  });

  return app;
}

/**
 * Run a Claude session and handle the conversation flow
 * Supports session resumption for multi-turn conversations
 */
async function runClaudeSession({ prompt, sessionKey, channel, threadTs, say, client, resumeSessionId = null }) {
  console.log('[CLAUDE] Starting session, prompt:', prompt?.substring(0, 50));
  console.log('[CLAUDE] Resume session ID:', resumeSessionId || 'none (new)');

  // Create session if it doesn't exist, otherwise it's already running
  if (!sessions.get(sessionKey)) {
    sessions.create(sessionKey, null);
  }

  try {
    // Post initial message in thread that we'll update with streaming content
    const initialMsg = await client.chat.postMessage({
      channel,
      thread_ts: threadTs,
      text: '_Thinking..._',
    });

    let currentText = '';
    let lastUpdateTime = Date.now();
    const UPDATE_INTERVAL = 1000; // Update Slack every 1 second

    const result = await runClaudeStreaming(
      prompt,
      config.claude.workingDir,
      sessionKey,
      async (chunk) => {
        currentText += chunk;
        const now = Date.now();

        // Throttle updates to avoid rate limits
        if (now - lastUpdateTime >= UPDATE_INTERVAL) {
          try {
            await client.chat.update({
              channel,
              ts: initialMsg.ts,
              text: currentText + '\n\n_..._',
            });
            lastUpdateTime = now;
          } catch (e) {
            console.error('[BOT] Failed to update message:', e.message);
          }
        }
      },
      config.claude.requirePermissions, // Pass permission mode
      resumeSessionId // Pass session ID for resumption
    );

    const { output, sessionId } = result;
    console.log('[CLAUDE] Complete, output length:', output?.length);
    console.log('[CLAUDE] Session ID for future resumption:', sessionId);

    // Hourglass reaction removed - using message updates instead

    // Skip completion reaction to reduce Activity feed noise
    // (the response itself indicates completion)

    // Final update with complete output
    const finalOutput = output.trim();
    if (finalOutput) {
      // Upload any images found in the response (in the thread)
      await uploadImagesFromText(finalOutput, channel, threadTs, client);

      // If output is too long, split into multiple messages
      if (finalOutput.length <= 3900) {
        await client.chat.update({
          channel,
          ts: initialMsg.ts,
          text: finalOutput,
        });
      } else {
        // Update first message with first chunk
        const chunks = splitMessage(finalOutput, 3900);
        await client.chat.update({
          channel,
          ts: initialMsg.ts,
          text: chunks[0],
        });
        // Post remaining chunks as new messages in thread
        for (let i = 1; i < chunks.length; i++) {
          await say({ text: chunks[i], thread_ts: threadTs });
        }
      }
    } else {
      await client.chat.update({
        channel,
        ts: initialMsg.ts,
        text: '_Claude completed without output._',
      });
    }

    // Store session ID for future resumption and mark as idle
    if (sessionId) {
      sessions.setClaudeSessionId(sessionKey, sessionId);
    }
    sessions.setIdle(sessionKey);
    console.log('[CLAUDE] Session now idle, ready for follow-up messages');

  } catch (err) {
    console.error('[CLAUDE] Error:', err);

    // Skip reactions to reduce Activity feed noise

    await say(`Error running Claude: ${err.message}`);

    sessions.kill(sessionKey, 'error');
  }
}

/**
 * Extract file paths from text and upload them to Slack
 * Supports images, markdown, code files, and more
 * @param {string} text - The response text
 * @param {string} channel - Slack channel ID
 * @param {string} threadTs - Thread timestamp to upload to
 * @param {object} client - Slack client
 * @returns {Promise<string>} Text with paths replaced by upload confirmations
 */
async function uploadImagesFromText(text, channel, threadTs, client) {
  // Match file paths - images, markdown, code files, etc.
  // Supports: images (png, jpg, gif, webp), docs (md, txt, pdf), code (py, js, ts, json, yaml, sh, html, css)
  const filePathRegex = /(?:(?:\/|\.\/)?[\w\-./]+\.(?:png|jpg|jpeg|gif|webp|md|txt|pdf|py|js|ts|jsx|tsx|json|yaml|yml|sh|bash|html|css|csv))/gi;
  const matches = text.match(filePathRegex) || [];

  // Dedupe paths
  const uniquePaths = [...new Set(matches)];

  for (let imagePath of uniquePaths) {
    // Convert relative paths to absolute using working directory
    if (!imagePath.startsWith('/')) {
      imagePath = path.join(config.claude.workingDir, imagePath);
    }

    // Check if file exists
    if (fs.existsSync(imagePath)) {
      try {
        console.log('[BOT] Uploading image:', imagePath);
        await client.files.uploadV2({
          channel_id: channel,
          thread_ts: threadTs,
          file: fs.createReadStream(imagePath),
          filename: path.basename(imagePath),
          title: path.basename(imagePath),
        });
        console.log('[BOT] Uploaded:', imagePath);
      } catch (e) {
        console.error('[BOT] Failed to upload image:', imagePath, e.message);
      }
    } else {
      console.log('[BOT] Image not found:', imagePath);
    }
  }

  return text;
}

/**
 * Split a long message into chunks
 * @param {string} text
 * @param {number} maxLength
 * @returns {string[]}
 */
function splitMessage(text, maxLength) {
  if (text.length <= maxLength) {
    return [text];
  }

  const chunks = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxLength) {
      chunks.push(remaining);
      break;
    }

    // Find a good break point (newline or space)
    let breakPoint = remaining.lastIndexOf('\n', maxLength);
    if (breakPoint === -1 || breakPoint < maxLength * 0.5) {
      breakPoint = remaining.lastIndexOf(' ', maxLength);
    }
    if (breakPoint === -1 || breakPoint < maxLength * 0.5) {
      breakPoint = maxLength;
    }

    chunks.push(remaining.substring(0, breakPoint));
    remaining = remaining.substring(breakPoint).trim();
  }

  return chunks;
}

module.exports = { createApp, sessions };
