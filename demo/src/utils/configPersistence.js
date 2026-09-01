/**
 * Configuration persistence utility using localStorage
 * Saves and loads user configuration across browser sessions
 */

const CONFIG_STORAGE_KEY = 'data2mcp_user_config';
const CONFIG_VERSION = '1.0';

/**
 * Save user configuration to localStorage
 * @param {Object} config - Configuration object containing datasets, llmConfig, etc.
 */
export function saveConfig(config) {
  try {
    const data = {
      version: CONFIG_VERSION,
      timestamp: Date.now(),
      ...config
    };
    localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(data));
    return true;
  } catch (error) {
    console.error('Failed to save config to localStorage:', error);
    return false;
  }
}

/**
 * Load user configuration from localStorage
 * @returns {Object|null} Saved configuration or null if not found
 */
export function loadConfig() {
  try {
    const stored = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!stored) return null;

    const data = JSON.parse(stored);

    // Version check for future migrations
    if (data.version !== CONFIG_VERSION) {
      console.warn('Config version mismatch, using stored config anyway');
    }

    // Remove metadata before returning
    const config = { ...data };
    delete config.version;
    delete config.timestamp;
    return config;
  } catch (error) {
    console.error('Failed to load config from localStorage:', error);
    return null;
  }
}

/**
 * Clear saved configuration from localStorage
 */
export function clearConfig() {
  try {
    localStorage.removeItem(CONFIG_STORAGE_KEY);
    return true;
  } catch (error) {
    console.error('Failed to clear config from localStorage:', error);
    return false;
  }
}

/**
 * Check if there is a saved configuration
 * @returns {boolean} True if config exists
 */
export function hasConfig() {
  try {
    return localStorage.getItem(CONFIG_STORAGE_KEY) !== null;
  } catch {
    return false;
  }
}

/**
 * Get metadata about saved config
 * @returns {Object|null} Metadata (version, timestamp) or null
 */
export function getConfigMetadata() {
  try {
    const stored = localStorage.getItem(CONFIG_STORAGE_KEY);
    if (!stored) return null;

    const data = JSON.parse(stored);
    return {
      version: data.version,
      timestamp: data.timestamp,
      savedAt: data.timestamp ? new Date(data.timestamp).toLocaleString() : 'Unknown'
    };
  } catch (error) {
    console.error('Failed to get config metadata:', error);
    return null;
  }
}
