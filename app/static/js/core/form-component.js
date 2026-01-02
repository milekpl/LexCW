/**
 * FormComponent - Base Class for Form Managers
 *
 * Provides standardized lifecycle management and event communication
 * for form components. All form managers should extend this class.
 *
 * Usage:
 *   class SenseManager extends FormComponent {
 *       static componentName = 'sense';
 *       static dependencies = ['field-visibility'];
 *
 *       setupEventListeners() {
 *           this.on('sense:add', this.handleAddSense.bind(this));
 *           this.on('form:dirty', this.handleFormDirty.bind(this));
 *       }
 *   }
 *
 *   // Initialize
 *   const senseManager = new SenseManager('#senses-container');
 *   senseManager.init();
 */

class FormComponent {
    /**
     * Component name (used for event namespacing)
     * @type {string}
     */
    static componentName = 'base';

    /**
     * Array of component names this depends on
     * @type {string[]}
     */
    static dependencies = [];

    /**
     * Create a new FormComponent
     * @param {string|HTMLElement} elementOrSelector - Element or CSS selector
     * @param {Object} options - Configuration options
     */
    constructor(elementOrSelector, options = {}) {
        // Get the element
        if (typeof elementOrSelector === 'string') {
            this.element = document.querySelector(elementOrSelector);
        } else if (elementOrSelector instanceof HTMLElement) {
            this.element = elementOrSelector;
        } else {
            this.element = null;
            Logger.warn(`[${this.constructor.componentName}] Invalid element:`, elementOrSelector);
        }

        this.options = options;
        this.eventBus = options.eventBus || window.eventBus;
        this._listeners = [];
        this._boundMethods = new Set();
        this._isInitialized = false;
        this._isDestroyed = false;

        // Bind default methods
        this.bindMethods();
    }

    /**
     * Bind methods that will be used as event handlers
     * Override in subclass to bind specific methods
     */
    bindMethods() {
        // Default no-op - override in subclass if needed
    }

    /**
     * Initialize the component
     * @returns {FormComponent} this for chaining
     */
    init() {
        if (this._isInitialized || this._isDestroyed) {
            Logger.warn(`[${this.constructor.componentName}] Already initialized or destroyed`);
            return this;
        }

        // Check for element
        if (!this.element) {
            Logger.warn(`[${this.constructor.componentName}] Element not found, skipping init`);
            return this;
        }

        try {
            this.setupEventListeners();
            this._isInitialized = true;
            Logger.debug(`[${this.constructor.componentName}] Initialized`);
            this.emit('initialized');
        } catch (error) {
            Logger.error(`[${this.constructor.componentName}] Init error:`, error);
        }

        return this;
    }

    /**
     * Set up event listeners for the component
     * Override in subclass
     */
    setupEventListeners() {
        // Override in subclass
    }

    /**
     * Destroy the component and clean up
     */
    destroy() {
        if (this._isDestroyed) return;

        // Remove all event listeners
        this._listeners.forEach(({ event, handler }) => {
            this.element?.removeEventListener(event, handler);
        });
        this._listeners = [];

        // Unsubscribe from event bus
        this.eventBus.removeAllListeners(`${this.constructor.componentName}:*`);

        this._isDestroyed = true;
        this._isInitialized = false;
        Logger.debug(`[${this.constructor.componentName}] Destroyed`);
    }

    /**
     * Emit an event through the event bus
     * @param {string} event - Event name (will be namespaced with component name)
     * @param {Object} data - Event data
     */
    emit(event, data = {}) {
        const namespacedEvent = `${this.constructor.componentName}:${event}`;
        this.eventBus.emit(namespacedEvent, {
            ...data,
            _source: this.constructor.componentName
        });
    }

    /**
     * Subscribe to an event
     * @param {string} event - Event name (will be namespaced with component name)
     * @param {Function} handler - Handler function
     * @returns {Function} Unsubscribe function
     */
    on(event, handler) {
        const namespacedEvent = `${this.constructor.componentName}:${event}`;

        const listener = (e) => {
            handler(e.detail);
        };

        this._listeners.push({ event: namespacedEvent, handler: listener });

        // Also register with event bus
        const unsubscribe = this.eventBus.on(namespacedEvent, handler);

        // Return unsubscribe function that cleans up both
        return () => {
            const idx = this._listeners.findIndex(l => l.event === namespacedEvent && l.handler === handler);
            if (idx > -1) this._listeners.splice(idx, 1);
            unsubscribe();
        };
    }

    /**
     * Subscribe to an event once
     * @param {string} event - Event name (will be namespaced with component name)
     * @param {Function} handler - Handler function
     * @returns {Function} Unsubscribe function
     */
    once(event, handler) {
        const namespacedEvent = `${this.constructor.componentName}:${event}`;
        return this.eventBus.once(namespacedEvent, handler);
    }

    /**
     * Subscribe to global events (not namespaced)
     * @param {string} event - Event name
     * @param {Function} handler - Handler function
     * @returns {Function} Unsubscribe function
     */
    onGlobal(event, handler) {
        return this.eventBus.on(event, handler);
    }

    /**
     * Add DOM event listener with automatic cleanup
     * @param {string} event - DOM event name
     * @param {Function} handler - Handler function
     * @param {Object} options - Event listener options
     * @returns {Function} Unsubscribe function
     */
    addDomListener(event, handler, options = {}) {
        if (!this.element) return () => {};

        this.element.addEventListener(event, handler, options);
        this._listeners.push({ event, handler, isDom: true });

        return () => {
            this.element?.removeEventListener(event, handler, options);
            const idx = this._listeners.findIndex(l => l.event === event && l.handler === handler);
            if (idx > -1) this._listeners.splice(idx, 1);
        };
    }

    /**
     * Query a single element within the component
     * @param {string} selector - CSS selector
     * @returns {HTMLElement|null}
     */
    query(selector) {
        return this.element?.querySelector(selector);
    }

    /**
     * Query all elements within the component
     * @param {string} selector - CSS selector
     * @returns {NodeList}
     */
    queryAll(selector) {
        return this.element?.querySelectorAll(selector) || [];
    }

    /**
     * Get component state for debugging
     * @returns {Object}
     */
    getState() {
        return {
            name: this.constructor.componentName,
            initialized: this._isInitialized,
            destroyed: this._isDestroyed,
            hasElement: !!this.element,
            listenerCount: this._listeners.length
        };
    }

    /**
     * Check if component is ready
     * @returns {boolean}
     */
    isReady() {
        return this._isInitialized && !this._isDestroyed;
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FormComponent;
}

// Make available globally
window.FormComponent = FormComponent;
