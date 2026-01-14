/**
 * FormEventBus - Centralized Event Communication System
 *
 * Provides a publish-subscribe pattern for communication between
 * loosely-coupled form components. Replaces direct window.* calls
 * with event-based communication.
 *
 * Usage:
 *   // Publishing events
 *   eventBus.emit('sense:added', { index: 2, senseId: 'abc123' });
 *   eventBus.emit('form:dirty', { field: 'lexical-unit' });
 *
 *   // Subscribing to events
 *   const unsubscribe = eventBus.on('sense:added', (data) => {
 *       console.log('Sense added at index:', data.index);
 *   });
 *
 *   // One-time subscriptions
 *   eventBus.once('form:initialized', () => {
 *       console.log('Form is ready');
 *   });
 *
 *   // Unsubscribing
 *   unsubscribe();
 */

class FormEventBus {
    constructor() {
        this._events = new Map();
        this._onceEvents = new Map();
        this._wildcardHandlers = [];
    }

    /**
     * Subscribe to an event
     * @param {string} event - Event name
     * @param {Function} callback - Handler function
     * @returns {Function} Unsubscribe function
     */
    on(event, callback) {
        if (typeof callback !== 'function') {
            Logger.warn('[FormEventBus] Callback must be a function:', event);
            return () => {};
        }

        if (!this._events.has(event)) {
            this._events.set(event, new Set());
        }
        this._events.get(event).add(callback);

        // Return unsubscribe function
        return () => {
            this.off(event, callback);
        };
    }

    /**
     * Subscribe to an event once (auto-unsubscribes after first call)
     * @param {string} event - Event name
     * @param {Function} callback - Handler function
     * @returns {Function} Unsubscribe function
     */
    once(event, callback) {
        if (typeof callback !== 'function') {
            Logger.warn('[FormEventBus] Callback must be a function:', event);
            return () => {};
        }

        if (!this._onceEvents.has(event)) {
            this._onceEvents.set(event, new Set());
        }
        this._onceEvents.get(event).add(callback);

        // Return unsubscribe function
        return () => {
            this._onceEvents.get(event)?.delete(callback);
        };
    }

    /**
     * Unsubscribe from an event
     * @param {string} event - Event name
     * @param {Function} callback - Handler function to remove
     */
    off(event, callback) {
        if (this._events.has(event)) {
            this._events.get(event).delete(callback);
        }
        if (this._onceEvents.has(event)) {
            this._onceEvents.get(event).delete(callback);
        }
    }

    /**
     * Emit an event
     * @param {string} event - Event name
     * @param {Object} data - Event data payload
     */
    emit(event, data = {}) {
        // Dispatch CustomEvent for DOM-based listeners
        if (typeof document !== 'undefined') {
            const eventObj = new CustomEvent(event, {
                detail: data,
                bubbles: true,
                cancelable: true
            });
            document.dispatchEvent(eventObj);
        }

        // Call registered handlers
        if (this._events.has(event)) {
            this._events.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    Logger.error('[FormEventBus] Handler error:', event, error);
                }
            });
        }

        // Call one-time handlers and remove them
        if (this._onceEvents.has(event)) {
            this._onceEvents.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    Logger.error('[FormEventBus] One-time handler error:', event, error);
                }
            });
            this._onceEvents.delete(event);
        }

        // Call wildcard handlers for all events (with event name)
        this._wildcardHandlers.forEach(handler => {
            try {
                handler(event, data);
            } catch (error) {
                Logger.error('[FormEventBus] Wildcard handler error:', error);
            }
        });
    }

    /**
     * Subscribe to all events (wildcard)
     * @param {Function} callback - Handler receives (event, data)
     * @returns {Function} Unsubscribe function
     */
    onAny(callback) {
        if (typeof callback !== 'function') {
            Logger.warn('[FormEventBus] Wildcard callback must be a function');
            return () => {};
        }
        this._wildcardHandlers.push(callback);
        return () => {
            const index = this._wildcardHandlers.indexOf(callback);
            if (index > -1) {
                this._wildcardHandlers.splice(index, 1);
            }
        };
    }

    /**
     * Remove all listeners for an event or all events
     * @param {string} [event] - Event name (optional, if omitted clears all)
     */
    removeAllListeners(event) {
        if (event) {
            this._events.delete(event);
            this._onceEvents.delete(event);
        } else {
            this._events.clear();
            this._onceEvents.clear();
            this._wildcardHandlers = [];
        }
    }

    /**
     * Get listener count for an event
     * @param {string} event - Event name
     * @returns {number} Number of listeners
     */
    listenerCount(event) {
        const regularCount = this._events.get(event)?.size || 0;
        const onceCount = this._onceEvents.get(event)?.size || 0;
        return regularCount + onceCount;
    }

    /**
     * Check if event has listeners
     * @param {string} event - Event name
     * @returns {boolean} True if event has listeners
     */
    hasListeners(event) {
        return this.listenerCount(event) > 0;
    }
}

// Create singleton instance
const eventBus = new FormEventBus();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { FormEventBus, eventBus };
}

// Make available globally
window.FormEventBus = FormEventBus;
window.eventBus = eventBus;
