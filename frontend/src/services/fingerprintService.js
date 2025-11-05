import FingerprintJS from '@fingerprintjs/fingerprintjs';
import { v4 as uuidv4 } from './uuid';
import { LOCAL_ID_KEY } from '../config';

/**
 * FingerprintService manages device identification
 */
class FingerprintService {
  constructor() {
    this.fpPromise = null;
    this.visitorId = null;
    this.localId = null;
  }

  /**
   * Initialize FingerprintJS
   */
  async initialize() {
    if (this.fpPromise) {
      return;
    }

    this.fpPromise = FingerprintJS.load();
  }

  /**
   * Get or generate local ID
   */
  getLocalId() {
    if (this.localId) {
      return this.localId;
    }

    let localId = localStorage.getItem(LOCAL_ID_KEY);

    if (!localId) {
      localId = uuidv4();
      localStorage.setItem(LOCAL_ID_KEY, localId);
    }

    this.localId = localId;
    return localId;
  }

  /**
   * Get visitor ID from FingerprintJS
   */
  async getVisitorId() {
    if (this.visitorId) {
      return this.visitorId;
    }

    await this.initialize();
    const fp = await this.fpPromise;
    const result = await fp.get();

    this.visitorId = result.visitorId;
    return this.visitorId;
  }

  /**
   * Get both visitor ID and local ID
   */
  async getIdentifiers() {
    const visitorId = await this.getVisitorId();
    const localId = this.getLocalId();

    return { visitorId, localId };
  }
}

export default new FingerprintService();
