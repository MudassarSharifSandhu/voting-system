import { API_BASE_URL } from '../config';

/**
 * VoteService handles vote submission
 */
class VoteService {
  /**
   * Submit a vote to the backend
   */
  async submitVote(contestant, fingerprint, token, recaptchaToken = null) {
    const response = await fetch(`${API_BASE_URL}/vote`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Vote-Token': token,
      },
      body: JSON.stringify({
        contestant,
        fingerprint,
        recaptcha_token: recaptchaToken || '',  // Required field, send empty string if not suspicious
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to submit vote');
    }

    return data;
  }
}

export default new VoteService();
