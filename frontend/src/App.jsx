import React, { useState, useEffect } from 'react';
import fingerprintService from './services/fingerprintService';
import tokenService from './services/tokenService';
import voteService from './services/voteService';
import { API_BASE_URL } from './config';

function App() {
  const [contestant, setContestant] = useState('');
  const [message, setMessage] = useState(null);
  const [messageType, setMessageType] = useState(''); // 'success', 'error', 'warning'
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [votesRemaining, setVotesRemaining] = useState(3);
  const [identifiers, setIdentifiers] = useState(null);
  const [isSuspicious, setIsSuspicious] = useState(false);
  const [recaptchaSiteKey, setRecaptchaSiteKey] = useState(null);
  const [recaptchaToken, setRecaptchaToken] = useState(null);
  const [recaptchaWidgetId, setRecaptchaWidgetId] = useState(null);
  const [recaptchaLoading, setRecaptchaLoading] = useState(false);

  const allowedContestants = [
    'Jones', 'Smith', 'Johnson', 'Williams', 'Brown',
    'Davis', 'Miller', 'Wilson', 'Moore', 'Taylor'
  ];

  // Initialize on component mount
  useEffect(() => {
    initializeSession();
  }, []);

  // Render reCAPTCHA widget when site key is loaded
  useEffect(() => {
    if (isSuspicious && recaptchaSiteKey && window.grecaptcha) {
      // Small delay to ensure container is rendered
      const timer = setTimeout(() => {
        // Clear any existing widget
        if (recaptchaWidgetId !== null && window.grecaptcha) {
          try {
            window.grecaptcha.reset(recaptchaWidgetId);
          } catch (e) {
            // Widget might not exist, ignore
          }
        }

        // Render new widget
        try {
          const widgetId = window.grecaptcha.render('recaptcha-container', {
            'sitekey': recaptchaSiteKey,
            'callback': (token) => {
              setRecaptchaToken(token);
            },
            'expired-callback': () => {
              setRecaptchaToken(null);
            },
            'error-callback': () => {
              setRecaptchaToken(null);
            }
          });
          setRecaptchaWidgetId(widgetId);
        } catch (e) {
          console.error('Failed to render reCAPTCHA:', e);
        }
      }, 100);

      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSuspicious, recaptchaSiteKey]);

  const loadRecaptchaSiteKey = async () => {
    try {
      setRecaptchaLoading(true);
      const response = await fetch(`${API_BASE_URL}/captcha/site-key`);
      if (!response.ok) {
        throw new Error('Failed to load reCAPTCHA site key');
      }
      const data = await response.json();
      setRecaptchaSiteKey(data.site_key);
      setRecaptchaToken(null); // Clear previous token
    } catch (error) {
      console.error('Failed to load reCAPTCHA site key:', error);
      setMessage('Failed to load reCAPTCHA. Please refresh the page.');
      setMessageType('error');
    } finally {
      setRecaptchaLoading(false);
    }
  };

  const initializeSession = async () => {
    try {
      setLoading(true);

      // Get device identifiers
      const ids = await fingerprintService.getIdentifiers();
      setIdentifiers(ids);

      // Initialize token and get current vote count
      const tokenData = await tokenService.initializeToken(ids.visitorId, ids.localId);

      // Update votes remaining based on IP-level count (stricter limit)
      // Use the maximum of device votes or IP votes to show the correct limit
      const votesUsedDevice = tokenData.votes_used || 0;
      const votesUsedIP = tokenData.votes_used_from_ip || 0;
      const maxVotes = 3; // Should match MAX_VOTES_PER_IP from backend

      // Show whichever limit is closer to being reached
      const actualVotesUsed = Math.max(votesUsedDevice, votesUsedIP);
      setVotesRemaining(maxVotes - actualVotesUsed);

      // Check if session is suspicious and load reCAPTCHA if needed
      setIsSuspicious(tokenData.is_suspicious || false);
      if (tokenData.is_suspicious) {
        await loadRecaptchaSiteKey();
      }

      setLoading(false);
    } catch (error) {
      console.error('Initialization error:', error);
      setMessage(error.message || 'Failed to initialize session');
      setMessageType('error');
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Clear previous messages
    setMessage(null);
    setMessageType('');

    // Validate input
    if (!contestant.trim()) {
      setMessage('Please enter a contestant last name');
      setMessageType('error');
      return;
    }

    try {
      setSubmitting(true);

      // Ensure we have valid token (refresh if needed)
      const session = await tokenService.ensureValidToken(
        identifiers.visitorId,
        identifiers.localId
      );

      // Check if session is suspicious and reCAPTCHA is required
      if (session.is_suspicious) {
        setIsSuspicious(true);
        
        // If no reCAPTCHA site key loaded, load it
        if (!recaptchaSiteKey) {
          await loadRecaptchaSiteKey();
        }

        // Validate reCAPTCHA token
        if (!recaptchaToken) {
          setMessage('Please complete the reCAPTCHA verification to continue.');
          setMessageType('error');
          return;
        }
      }

      // Submit vote with reCAPTCHA token if suspicious
      const result = await voteService.submitVote(
        contestant,
        session.fingerprint,
        session.token,
        session.is_suspicious ? recaptchaToken : null
      );

      // Handle response
      if (result.success) {
        setMessage(result.message);
        setMessageType('success');
        setContestant(''); // Clear input on success
        setRecaptchaToken(null); // Clear reCAPTCHA token

        if (result.votes_remaining !== undefined) {
          setVotesRemaining(result.votes_remaining);
        }

        // Reset reCAPTCHA widget for next vote if still suspicious
        if (isSuspicious && recaptchaWidgetId !== null && window.grecaptcha) {
          window.grecaptcha.reset(recaptchaWidgetId);
        }
      } else if (result.requires_verification) {
        setMessage(result.message + ' Please complete verification.');
        setMessageType('warning');
      }
    } catch (error) {
      console.error('Vote submission error:', error);

      // Handle CAPTCHA errors - session may have become suspicious
      if (error.message.includes('CAPTCHA') || error.message.includes('verification required')) {
        setMessage(error.message);
        setMessageType('error');
        
        // Refresh token to get updated is_suspicious status
        try {
          const updatedSession = await tokenService.initializeToken(
            identifiers.visitorId,
            identifiers.localId
          );
          
          // Check if session is now suspicious
          if (updatedSession.is_suspicious) {
            setIsSuspicious(true);
            
            // Load reCAPTCHA if not already loaded
            if (!recaptchaSiteKey) {
              await loadRecaptchaSiteKey();
            }
            
            setMessage('Security verification required. Please complete the reCAPTCHA challenge.');
            setMessageType('warning');
          } else {
            // Reset reCAPTCHA widget if it exists
            if (recaptchaWidgetId !== null && window.grecaptcha) {
              window.grecaptcha.reset(recaptchaWidgetId);
            }
          }
        } catch (refreshError) {
          console.error('Failed to refresh token:', refreshError);
          // Reset reCAPTCHA widget
          if (recaptchaWidgetId !== null && window.grecaptcha) {
            window.grecaptcha.reset(recaptchaWidgetId);
          }
        }
      }
      // Handle token expiry
      else if (error.message.includes('expired') || error.message.includes('Invalid token')) {
        try {
          // Refresh token and retry
          await tokenService.initializeToken(identifiers.visitorId, identifiers.localId);
          setMessage('Session refreshed. Please try again.');
          setMessageType('warning');
        } catch (refreshError) {
          setMessage('Session expired. Please refresh the page.');
          setMessageType('error');
        }
      } else {
        setMessage(error.message || 'Failed to submit vote');
        setMessageType('error');
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="container">
        <div className="loading">
          <h2>Initializing Voting System...</h2>
          <p>Please wait while we set up your session</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <h1>America's Got Talent</h1>
      <p className="subtitle">Vote for your favorite contestant</p>

      {message && (
        <div className={`message ${messageType}`}>
          {message}
        </div>
      )}

      {isSuspicious && (
        <div className="captcha-container">
          <div className="captcha-warning">
            <strong>⚠️ Security Verification Required</strong>
            <p>Your session has been flagged for additional security verification. Please complete the reCAPTCHA challenge below.</p>
          </div>
          {recaptchaLoading ? (
            <div className="captcha-loading">Loading reCAPTCHA...</div>
          ) : recaptchaSiteKey ? (
            <div className="captcha-challenge">
              <div id="recaptcha-container"></div>
              <button
                type="button"
                onClick={() => {
                  if (recaptchaWidgetId !== null && window.grecaptcha) {
                    window.grecaptcha.reset(recaptchaWidgetId);
                    setRecaptchaToken(null);
                  }
                }}
                disabled={recaptchaLoading}
                className="captcha-refresh"
              >
                Reset reCAPTCHA
              </button>
            </div>
          ) : null}
        </div>
      )}

      <form className="form" onSubmit={handleSubmit}>
        <div className="input-group">
          <label htmlFor="contestant">Contestant Last Name</label>
          <input
            id="contestant"
            type="text"
            value={contestant}
            onChange={(e) => setContestant(e.target.value)}
            placeholder="Enter last name (e.g., Smith)"
            disabled={submitting || votesRemaining === 0}
            autoComplete="off"
          />
        </div>

        <button type="submit" disabled={
          submitting || 
          votesRemaining === 0 || 
          (isSuspicious && !recaptchaToken)
        }>
          {submitting ? 'Submitting...' : votesRemaining === 0 ? 'No Votes Remaining' : 'Submit Vote'}
        </button>
      </form>

      <div className="votes-info">
        <strong>{votesRemaining}</strong>
        {votesRemaining === 1 ? 'vote remaining' : 'votes remaining'}
      </div>

      <div className="allowed-contestants">
        <h3>Eligible Contestants:</h3>
        <div className="contestants-list">
          {allowedContestants.map((name) => (
            <span key={name} className="contestant-tag">
              {name}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;
