/**
 * Session Manager - Tracks active Claude sessions per Slack thread
 *
 * Each session represents an ongoing Claude conversation that may be:
 * - Running: Claude is executing
 * - Awaiting approval: Claude asked for permission, waiting for user response
 */

class SessionManager {
  /**
   * @param {number} timeoutMs - Session timeout in ms. 0 = no timeout (sessions persist forever)
   */
  constructor(timeoutMs = 0) {
    this.sessions = new Map();
    this.timeoutMs = timeoutMs; // 0 means no timeout
  }

  /**
   * Create a new session for a thread
   * @param {string} threadKey - Slack thread_ts or message ts
   * @param {object} claudeProcess - The spawned Claude process
   * @returns {object} Session object
   */
  create(threadKey, claudeProcess) {
    const session = {
      threadKey,
      process: claudeProcess,
      state: 'running', // 'running' | 'awaiting_approval' | 'completed' | 'idle'
      output: '',
      pendingApproval: null, // Callback to send approval to Claude
      claudeSessionId: null, // Claude SDK session ID for resumption
      createdAt: Date.now(),
      lastActivityAt: Date.now(),
    };

    this.sessions.set(threadKey, session);
    this._scheduleTimeout(threadKey);

    return session;
  }

  /**
   * Store Claude session ID for resumption
   * @param {string} threadKey
   * @param {string} sessionId - Claude SDK session ID
   */
  setClaudeSessionId(threadKey, sessionId) {
    const session = this.get(threadKey);
    if (session) {
      session.claudeSessionId = sessionId;
      session.lastActivityAt = Date.now();
    }
  }

  /**
   * Get Claude session ID for resumption
   * @param {string} threadKey
   * @returns {string|null}
   */
  getClaudeSessionId(threadKey) {
    const session = this.get(threadKey);
    return session?.claudeSessionId || null;
  }

  /**
   * Mark session as idle (ready for follow-up messages)
   * @param {string} threadKey
   */
  setIdle(threadKey) {
    const session = this.get(threadKey);
    if (session) {
      session.state = 'idle';
      session.lastActivityAt = Date.now();
    }
  }

  /**
   * Check if session is idle and can accept new messages
   * @param {string} threadKey
   * @returns {boolean}
   */
  isIdle(threadKey) {
    const session = this.get(threadKey);
    return session && session.state === 'idle';
  }

  /**
   * Set session back to running
   * @param {string} threadKey
   */
  setRunning(threadKey) {
    const session = this.get(threadKey);
    if (session) {
      session.state = 'running';
      session.lastActivityAt = Date.now();
    }
  }

  /**
   * Get session by thread key
   * @param {string} threadKey
   * @returns {object|null}
   */
  get(threadKey) {
    return this.sessions.get(threadKey) || null;
  }

  /**
   * Check if a session exists and is awaiting approval
   * @param {string} threadKey
   * @returns {boolean}
   */
  isAwaitingApproval(threadKey) {
    const session = this.get(threadKey);
    return session && session.state === 'awaiting_approval';
  }

  /**
   * Set session to awaiting approval state
   * @param {string} threadKey
   * @param {function} sendApprovalCallback - Called with user's response
   */
  setAwaitingApproval(threadKey, sendApprovalCallback) {
    const session = this.get(threadKey);
    if (session) {
      session.state = 'awaiting_approval';
      session.pendingApproval = sendApprovalCallback;
      session.lastActivityAt = Date.now();
    }
  }

  /**
   * Send approval to a waiting session
   * @param {string} threadKey
   * @param {string} response - User's approval response
   * @returns {boolean} Whether approval was sent
   */
  sendApproval(threadKey, response) {
    const session = this.get(threadKey);
    if (session && session.state === 'awaiting_approval' && session.pendingApproval) {
      session.pendingApproval(response);
      session.state = 'running';
      session.pendingApproval = null;
      session.lastActivityAt = Date.now();
      return true;
    }
    return false;
  }

  /**
   * Append output to session
   * @param {string} threadKey
   * @param {string} text
   */
  appendOutput(threadKey, text) {
    const session = this.get(threadKey);
    if (session) {
      session.output += text;
      session.lastActivityAt = Date.now();
    }
  }

  /**
   * Mark session as completed and remove it
   * @param {string} threadKey
   * @returns {string} Final output
   */
  complete(threadKey) {
    const session = this.get(threadKey);
    if (session) {
      session.state = 'completed';
      const output = session.output;
      this.sessions.delete(threadKey);
      return output;
    }
    return '';
  }

  /**
   * Kill session and clean up
   * @param {string} threadKey
   * @param {string} reason
   */
  kill(threadKey, reason = 'timeout') {
    const session = this.get(threadKey);
    if (session) {
      if (session.process && !session.process.killed) {
        session.process.kill('SIGTERM');
      }
      this.sessions.delete(threadKey);
      console.log(`Session ${threadKey} killed: ${reason}`);
    }
  }

  /**
   * Schedule timeout for inactive sessions
   * @private
   */
  _scheduleTimeout(threadKey) {
    // If timeoutMs is 0, sessions never expire
    if (this.timeoutMs === 0) {
      return;
    }

    setTimeout(() => {
      const session = this.get(threadKey);
      if (session) {
        const inactive = Date.now() - session.lastActivityAt;
        if (inactive >= this.timeoutMs) {
          this.kill(threadKey, `inactive for ${Math.round(inactive / 1000)}s`);
        } else {
          // Reschedule
          this._scheduleTimeout(threadKey);
        }
      }
    }, this.timeoutMs);
  }

  /**
   * Get all active sessions (for debugging)
   * @returns {Array}
   */
  listActive() {
    return Array.from(this.sessions.entries()).map(([key, session]) => ({
      threadKey: key,
      state: session.state,
      age: Date.now() - session.createdAt,
    }));
  }
}

module.exports = SessionManager;
