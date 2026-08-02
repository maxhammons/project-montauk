/**
 * Permission Parser - Detects and formats Claude's permission prompts
 *
 * Claude outputs permission requests in various formats. This module
 * detects these patterns and formats them nicely for Slack.
 */

// Patterns that indicate Claude is asking for permission
const PERMISSION_PATTERNS = [
  // Tool approval patterns
  /Allow\s+(\w+)\s+tool\?/i,
  /Allow\s+(\w+)\(([^)]*)\)\?/i,
  /\[Y\/n\]/i,
  /\[y\/N\]/i,
  /Press Enter to allow/i,
  /Do you want to proceed\?/i,
  /Allow this edit\?/i,
  /Allow this action\?/i,

  // File operation patterns
  /wants? to (edit|write|create|delete)/i,
  /wants? to run/i,

  // Bash command patterns
  /Allow Bash\(/i,
  /Execute command:/i,
];

/**
 * Check if text contains a permission request
 * @param {string} text - Output from Claude
 * @returns {boolean}
 */
function isPermissionRequest(text) {
  return PERMISSION_PATTERNS.some((pattern) => pattern.test(text));
}

/**
 * Extract permission details from Claude's output
 * @param {string} text - Output from Claude
 * @returns {object} Parsed permission info
 */
function parsePermission(text) {
  const result = {
    isPermission: false,
    toolName: null,
    toolArgs: null,
    action: null,
    rawPrompt: text,
  };

  // Check for tool patterns: Allow ToolName(args)?
  const toolMatch = text.match(/Allow\s+(\w+)\(([^)]*)\)\?/i);
  if (toolMatch) {
    result.isPermission = true;
    result.toolName = toolMatch[1];
    result.toolArgs = toolMatch[2];
    result.action = `${toolMatch[1]}(${toolMatch[2]})`;
    return result;
  }

  // Check for simple tool: Allow ToolName tool?
  const simpleToolMatch = text.match(/Allow\s+(\w+)\s+tool\?/i);
  if (simpleToolMatch) {
    result.isPermission = true;
    result.toolName = simpleToolMatch[1];
    result.action = simpleToolMatch[1];
    return result;
  }

  // Check for file operations
  const fileOpMatch = text.match(/wants? to (edit|write|create|delete)\s+(.+)/i);
  if (fileOpMatch) {
    result.isPermission = true;
    result.action = `${fileOpMatch[1]} ${fileOpMatch[2].trim()}`;
    return result;
  }

  // Generic permission check
  if (isPermissionRequest(text)) {
    result.isPermission = true;
    result.action = 'perform an action';
  }

  return result;
}

/**
 * Format permission request for Slack display
 * @param {string} text - Raw output from Claude
 * @returns {string} Formatted Slack message
 */
function formatForSlack(text) {
  const parsed = parsePermission(text);

  if (!parsed.isPermission) {
    return null;
  }

  // Clean up the text for display
  let displayText = text.trim();

  // Truncate if too long
  if (displayText.length > 1500) {
    displayText = displayText.substring(0, 1500) + '\n... (truncated)';
  }

  const header = parsed.action
    ? `Claude wants to: *${parsed.action}*`
    : `Claude needs approval`;

  return [
    `${header}`,
    '',
    '```',
    displayText,
    '```',
    '',
    '_Reply with your decision:_',
    '• `yes` or `y` - approve',
    '• `no` or `n` - deny',
    '• Or type additional instructions',
  ].join('\n');
}

/**
 * Parse user's approval response
 * @param {string} response - User's Slack message
 * @returns {object} Parsed response
 */
function parseApprovalResponse(response) {
  const text = response.trim().toLowerCase();

  if (['yes', 'y', 'ok', 'approve', 'allow', 'sure', 'go ahead'].includes(text)) {
    return { approved: true, response: 'y' };
  }

  if (['no', 'n', 'deny', 'reject', 'cancel', 'stop'].includes(text)) {
    return { approved: false, response: 'n' };
  }

  // Treat any other text as additional instructions (still approving but with context)
  return { approved: true, response: response.trim() };
}

module.exports = {
  isPermissionRequest,
  parsePermission,
  formatForSlack,
  parseApprovalResponse,
};
