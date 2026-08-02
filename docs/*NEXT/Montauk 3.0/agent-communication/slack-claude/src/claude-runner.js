/**
 * Claude Runner - Uses Claude Agent SDK V1 for sessions with streaming
 *
 * Uses the V1 query() API which supports canUseTool for interactive permissions.
 * Maintains session state per Slack thread.
 */

const { query } = require('@anthropic-ai/claude-agent-sdk');
const path = require('path');
const fs = require('fs');
const { config } = require('../config');

// Store pending permission requests by thread key
// Each entry: { resolve, toolName, input, timestamp, messageTs }
const pendingPermissions = new Map();

// Permission timeout in ms (SDK has 60s limit, we use 55s to be safe)
const PERMISSION_TIMEOUT_MS = 55000;

// Callback for posting permission requests to Slack
// Set by bot.js via setPermissionCallback
let permissionCallback = null;

/**
 * Set the callback function for posting permission requests to Slack
 * @param {function} callback - async (threadKey, toolName, input) => Promise<void>
 */
function setPermissionCallback(callback) {
  permissionCallback = callback;
}

/**
 * Handle a permission response from Slack
 * @param {string} threadKey - The thread identifier
 * @param {string} response - User's response text (yes/no/y/n or custom)
 * @returns {boolean} Whether there was a pending permission to resolve
 */
function handlePermissionResponse(threadKey, response) {
  const pending = pendingPermissions.get(threadKey);
  if (!pending) {
    return false;
  }

  const normalizedResponse = response.toLowerCase().trim();
  const isApproved = ['yes', 'y', 'approve', 'allow', 'ok', 'sure', 'go ahead', 'do it'].some(
    word => normalizedResponse === word || normalizedResponse.startsWith(word + ' ')
  );

  pending.resolve({
    approved: isApproved,
    message: response,
  });

  pendingPermissions.delete(threadKey);
  return true;
}

/**
 * Check if there's a pending permission for a thread
 * @param {string} threadKey
 * @returns {boolean}
 */
function hasPendingPermission(threadKey) {
  return pendingPermissions.has(threadKey);
}

/**
 * Format tool input for display in Slack
 */
function formatToolInput(toolName, input) {
  if (toolName === 'Bash') {
    return `\`\`\`\n${input.command}\n\`\`\`${input.description ? `\n_${input.description}_` : ''}`;
  }
  if (toolName === 'Write' || toolName === 'Edit') {
    const preview = input.content?.substring(0, 200) || input.new_string?.substring(0, 200) || '';
    return `File: \`${input.file_path}\`\n\`\`\`\n${preview}${preview.length >= 200 ? '...' : ''}\n\`\`\``;
  }
  if (toolName === 'Read') {
    return `File: \`${input.file_path}\``;
  }
  // Default: show JSON
  return `\`\`\`json\n${JSON.stringify(input, null, 2).substring(0, 300)}\n\`\`\``;
}

/**
 * Run Claude query with streaming callback and permission handling
 *
 * @param {string} prompt - The user's message
 * @param {string} workingDir - Working directory
 * @param {string} threadKey - Thread identifier for session/permission tracking
 * @param {function} onChunk - Callback for each text chunk
 * @param {boolean} requirePermissions - If true, use default permission mode; if false, bypass
 * @param {string|null} resumeSessionId - Claude session ID to resume (for conversation continuity)
 * @returns {Promise<{output: string, sessionId: string|null}>} The response and session ID
 */
async function runClaudeStreaming(prompt, workingDir, threadKey, onChunk, requirePermissions = false, resumeSessionId = null) {
  console.log('[RUNNER] Starting streaming query');
  console.log('[RUNNER] Thread key:', threadKey);
  console.log('[RUNNER] Require permissions:', requirePermissions);
  console.log('[RUNNER] Resume session:', resumeSessionId || 'none (new session)');
  console.log('[RUNNER] Prompt:', prompt?.substring(0, 50));

  let outputText = '';
  let lastChunkTime = Date.now();
  let pendingText = '';
  const CHUNK_INTERVAL = 500;

  // Build plugins list from skills directory
  const skillsDir = config.claude.skillsDir;
  const plugins = [];
  const mcpServers = {};

  // Auto-discover skills from skills directory
  if (fs.existsSync(skillsDir)) {
    const skillDirs = fs.readdirSync(skillsDir, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory())
      .map(dirent => dirent.name);

    for (const skillName of skillDirs) {
      const skillPath = path.join(skillsDir, skillName);
      const skillMdPath = path.join(skillPath, 'SKILL.md');

      // Only add if SKILL.md exists (valid skill)
      if (fs.existsSync(skillMdPath)) {
        plugins.push({ type: 'local', path: skillPath });

        // Check for server.sh (MCP server)
        const serverPath = path.join(skillPath, 'server.sh');
        if (fs.existsSync(serverPath)) {
          mcpServers[skillName] = {
            type: 'stdio',
            command: serverPath,
            args: ['--headless'],
          };
        }
      }
    }
    console.log('[RUNNER] Loaded skills:', plugins.map(p => path.basename(p.path)).join(', '));
  }

  const options = {
    cwd: workingDir,
    maxTurns: 10,
    // Load project and local settings only (NOT user-level ~/.claude/)
    // This way the Stop hook from ~/.claude/settings.json won't affect Slack bot
    // Project permissions from .claude/settings.json are still loaded
    settingSources: ['project', 'local'],
    // Selectively enable hooks for Slack bot:
    // - UserPromptSubmit: Keep enabled (memory bank reminders, etc.)
    // - Stop: Disable (followup prompts don't make sense in Slack - users just send another message)
    // Add MCP servers for skills with servers
    mcpServers,
    // Load skills as plugins
    plugins,
  };

  // Add resume option if we have a previous session ID
  if (resumeSessionId) {
    options.resume = resumeSessionId;
    console.log('[RUNNER] Resuming session:', resumeSessionId);
  }

  console.log('[RUNNER] Settings sources:', options.settingSources.join(', '));
  console.log('[RUNNER] Permission mode:', requirePermissions ? 'default (with canUseTool callback)' : 'bypassPermissions');

  // Configure permission mode
  if (requirePermissions) {
    options.permissionMode = 'default';
    options.canUseTool = async (toolName, input) => {
      console.log('[RUNNER] Permission requested for:', toolName);

      // Auto-allow read-only tools
      if (['Read', 'Glob', 'Grep', 'WebSearch', 'WebFetch'].includes(toolName)) {
        console.log('[RUNNER] Auto-allowing read-only tool:', toolName);
        return { behavior: 'allow', updatedInput: input };
      }

      // Post to Slack and wait for response
      if (permissionCallback) {
        const formattedInput = formatToolInput(toolName, input);

        // Create a promise that will be resolved when user responds
        const permissionPromise = new Promise((resolve) => {
          pendingPermissions.set(threadKey, {
            resolve,
            toolName,
            input,
            timestamp: Date.now(),
          });

          // Set timeout
          setTimeout(() => {
            if (pendingPermissions.has(threadKey)) {
              pendingPermissions.delete(threadKey);
              resolve({ approved: false, message: 'Permission request timed out' });
            }
          }, PERMISSION_TIMEOUT_MS);
        });

        // Post permission request to Slack
        try {
          await permissionCallback(threadKey, toolName, formattedInput);
        } catch (err) {
          console.error('[RUNNER] Failed to post permission request:', err);
          return { behavior: 'deny', message: 'Failed to request permission via Slack' };
        }

        // Wait for user response
        const result = await permissionPromise;

        if (result.approved) {
          console.log('[RUNNER] Permission approved');
          return { behavior: 'allow', updatedInput: input };
        } else {
          console.log('[RUNNER] Permission denied:', result.message);
          return { behavior: 'deny', message: result.message || 'User denied permission' };
        }
      }

      // No callback set - deny by default
      return { behavior: 'deny', message: 'No permission handler configured' };
    };
  } else {
    options.permissionMode = 'bypassPermissions';
    options.allowDangerouslySkipPermissions = true;
  }

  let sessionId = null;

  try {
    const q = query({
      prompt,
      options,
    });

    for await (const msg of q) {
      // Capture session ID from init message
      if (msg.type === 'system' && msg.subtype === 'init' && msg.session_id) {
        sessionId = msg.session_id;
        console.log('[RUNNER] Got session ID:', sessionId);
      } else if (msg.type === 'assistant') {
        const content = msg.message?.content;
        if (Array.isArray(content)) {
          for (const block of content) {
            if (block.type === 'text') {
              outputText += block.text;
              pendingText += block.text;

              // Send chunks periodically
              const now = Date.now();
              if (now - lastChunkTime >= CHUNK_INTERVAL && pendingText.length > 0) {
                if (onChunk) {
                  await onChunk(pendingText);
                }
                pendingText = '';
                lastChunkTime = now;
              }
            }
          }
        }
      } else if (msg.type === 'result') {
        if (msg.subtype === 'success' && msg.result) {
          if (!outputText) {
            outputText = msg.result;
          }
        } else if (msg.subtype?.startsWith('error')) {
          console.error('[RUNNER] Error:', msg.errors);
          if (msg.errors?.length) {
            outputText = `Error: ${msg.errors.join(', ')}`;
          }
        }
      }
    }

    // Send any remaining text
    if (pendingText.length > 0 && onChunk) {
      await onChunk(pendingText);
    }

    console.log('[RUNNER] Complete, length:', outputText.length);
    console.log('[RUNNER] Session ID for resumption:', sessionId);
    return {
      output: outputText || 'No response from Claude.',
      sessionId,
    };

  } catch (err) {
    console.error('[RUNNER] Error:', err);
    // Clean up any pending permission
    pendingPermissions.delete(threadKey);
    throw err;
  }
}

/**
 * Simple wrapper for non-streaming use
 */
async function runClaudeSimple(prompt, workingDir, threadKey = 'default', requirePermissions = false, resumeSessionId = null) {
  return runClaudeStreaming(prompt, workingDir, threadKey, null, requirePermissions, resumeSessionId);
}

module.exports = {
  runClaudeStreaming,
  runClaudeSimple,
  setPermissionCallback,
  handlePermissionResponse,
  hasPendingPermission,
  formatToolInput,
};
