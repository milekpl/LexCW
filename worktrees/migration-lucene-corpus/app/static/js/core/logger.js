/**
 * Centralized Logger Utility
 *
 * Single source of truth for all logging in the application.
 * Eliminates scattered console.log statements across the codebase.
 *
 * Usage:
 *   Logger.debug('Debug message', data);
 *   Logger.info('Info message');
 *   Logger.warn('Warning message');
 *   Logger.error('Error message', error);
 *   Logger.time('operation');
 *   Logger.timeEnd('operation');
 */

const Logger = {
    // Toggle for debugging in development
    // Set to true to enable debug() output
    DEBUG: false,

    /**
     * Debug level logging - only outputs if DEBUG is true
     */
    debug: (...args) => {
        if (Logger.DEBUG) {
            console.debug('[DEBUG]', new Date().toISOString(), ...args);
        }
    },

    /**
     * Info level logging
     */
    info: (...args) => {
        console.info('[INFO]', new Date().toISOString(), ...args);
    },

    /**
     * Warning level logging
     */
    warn: (...args) => {
        console.warn('[WARN]', new Date().toISOString(), ...args);
    },

    /**
     * Error level logging
     */
    error: (...args) => {
        console.error('[ERROR]', new Date().toISOString(), ...args);
    },

    /**
     * Time tracking for performance measurement
     */
    time: (label) => {
        console.time(label);
    },

    /**
     * TimeEnd tracking for performance measurement
     */
    timeEnd: (label) => {
        console.timeEnd(label);
    },

    /**
     * Group related log messages
     */
    group: (label) => {
        console.group(label);
    },

    /**
     * End group
     */
    groupEnd: () => {
        console.groupEnd();
    }
};

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Logger;
}

// Also make available globally for legacy code
window.Logger = Logger;
