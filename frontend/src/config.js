/**
 * Application configuration
 * Loads environment variables with Vite's import.meta.env
 * 
 * Note: In Vite, environment variables must be prefixed with VITE_ to be exposed to the client
 */

// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// LocalStorage Keys
export const TOKEN_STORAGE_KEY = import.meta.env.VITE_TOKEN_STORAGE_KEY || 'agt_vote_session';
export const LOCAL_ID_KEY = import.meta.env.VITE_LOCAL_ID_KEY || 'agt_local_id';

