import { API_BASE_URL, TOKEN_STORAGE_KEY } from '../config';

/**
 * TokenService manages authentication tokens and session data
 */
class TokenService {
  /**
   * Get stored session data from localStorage
   */
  getSession() {
    try {
      const data = localStorage.getItem(TOKEN_STORAGE_KEY);
      return data ? JSON.parse(data) : null;
    } catch (error) {
      console.error('Error reading session:', error);
      return null;
    }
  }

  /**
   * Save session data to localStorage
   */
  setSession(sessionData) {
    try {
      localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(sessionData));
    } catch (error) {
      console.error('Error saving session:', error);
    }
  }

  /**
   * Clear session data from localStorage
   */
  clearSession() {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }

  /**
   * Check if the current token is expired
   */
  isTokenExpired(expiresAt) {
    if (!expiresAt) return true;
    const expiryTime = new Date(expiresAt).getTime();
    const now = Date.now();
    // Add 30 second buffer to refresh before actual expiry
    return now >= (expiryTime - 30000);
  }

  /**
   * Fetch a new token from the server
   */
  async fetchToken(visitorId, localId) {
    const response = await fetch(
      `${API_BASE_URL}/token?visitorId=${encodeURIComponent(visitorId)}&localId=${encodeURIComponent(localId)}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Token fetch failed' }));
      throw new Error(error.detail || 'Failed to fetch token');
    }

    const data = await response.json();
    return data;
  }

  /**
   * Initialize or refresh the token
   */
  async initializeToken(visitorId, localId) {
    // Always fetch fresh token data to get current votes_used
    // (even if token is still valid, we need to sync vote count)
    const tokenData = await this.fetchToken(visitorId, localId);

    const sessionData = {
      token: tokenData.token,
      fingerprint: tokenData.fingerprint,
      expires_at: tokenData.expires_at,
      votes_used: tokenData.votes_used || 0,
      votes_used_from_ip: tokenData.votes_used_from_ip || 0,
      is_suspicious: tokenData.is_suspicious || false,
    };

    this.setSession(sessionData);
    return sessionData;
  }

  /**
   * Ensure we have a valid token, refreshing if necessary
   */
  async ensureValidToken(visitorId, localId) {
    const session = this.getSession();

    if (!session || this.isTokenExpired(session.expires_at)) {
      return await this.initializeToken(visitorId, localId);
    }

    return session;
  }
}

export default new TokenService();
