/**
 * Generic reordering utility for multi-item lists in the dictionary form
 * Supports senses, pronunciations, examples, notes, etc.
 */
class ReorderingManager {
    constructor() {
        this.initEventListeners();
    }

    /**
     * Initialize event listeners for reordering buttons
     */
    initEventListeners() {
        document.addEventListener('click', (e) => {
            // Handle generic move up buttons
            if (e.target.closest('.move-up-btn')) {
                const button = e.target.closest('.move-up-btn');
                const itemType = button.dataset.itemType || 'item';
                this.moveItemUp(button, itemType);
                return;
            }

            // Handle generic move down buttons  
            if (e.target.closest('.move-down-btn')) {
                const button = e.target.closest('.move-down-btn');
                const itemType = button.dataset.itemType || 'item';
                this.moveItemDown(button, itemType);
                return;
            }

            // Legacy support for sense-specific buttons
            if (e.target.closest('.move-sense-up') || e.target.closest('.move-sense-down')) {
                // These are handled by the existing entry-form.js
                return;
            }
        });
    }

    /**
     * Move an item up in its container
     * @param {HTMLElement} button - The move up button
     * @param {string} itemType - Type of item being moved (for feedback)
     */
    moveItemUp(button, itemType) {
        const item = this.findItemContainer(button);
        if (!item) return;

        const prevItem = item.previousElementSibling;
        if (prevItem && this.isSameItemType(item, prevItem)) {
            const container = item.parentNode;
            container.insertBefore(item, prevItem);
            this.reindexItems(container, itemType);
            this.showSuccess(`${itemType} moved up successfully`);
        }
    }

    /**
     * Move an item down in its container
     * @param {HTMLElement} button - The move down button
     * @param {string} itemType - Type of item being moved (for feedback)
     */
    moveItemDown(button, itemType) {
        const item = this.findItemContainer(button);
        if (!item) return;

        const nextItem = item.nextElementSibling;
        if (nextItem && this.isSameItemType(item, nextItem)) {
            const container = item.parentNode;
            container.insertBefore(nextItem, item);
            this.reindexItems(container, itemType);
            this.showSuccess(`${itemType} moved down successfully`);
        }
    }

    /**
     * Find the item container from a button
     * @param {HTMLElement} button - The button that was clicked
     * @returns {HTMLElement|null} The item container
     */
    findItemContainer(button) {
        // Look for common item container patterns
        const patterns = [
            '.sense-item',
            '.pronunciation-item', 
            '.example-item',
            '.note-item',
            '.variant-item',
            '.etymology-item',
            '.relation-item',
            '.reorderable-item'
        ];

        for (const pattern of patterns) {
            const container = button.closest(pattern);
            if (container) return container;
        }

        return null;
    }

    /**
     * Check if two items are of the same type (have same class patterns)
     * @param {HTMLElement} item1 - First item
     * @param {HTMLElement} item2 - Second item
     * @returns {boolean} True if items are same type
     */
    isSameItemType(item1, item2) {
        const patterns = [
            'sense-item',
            'pronunciation-item',
            'example-item', 
            'note-item',
            'variant-item',
            'etymology-item',
            'relation-item',
            'reorderable-item'
        ];

        for (const pattern of patterns) {
            if (item1.classList.contains(pattern) && item2.classList.contains(pattern)) {
                return true;
            }
        }

        return false;
    }

    /**
     * Reindex items in a container after reordering
     * @param {HTMLElement} container - The container with items
     * @param {string} itemType - Type of items for specific reindexing logic
     */
    reindexItems(container, itemType) {
        const items = container.children;
        
        Array.from(items).forEach((item, newIndex) => {
            // Update data-index attributes
            if (item.dataset.index !== undefined) {
                item.dataset.index = newIndex;
            }
            if (item.dataset.senseIndex !== undefined) {
                item.dataset.senseIndex = newIndex;
            }
            if (item.dataset.exampleIndex !== undefined) {
                item.dataset.exampleIndex = newIndex;
            }

            // Update visual numbering based on item type
            this.updateVisualNumbering(item, newIndex, itemType);

            // Update form field names
            this.updateFieldNames(item, newIndex, itemType);
        });

        // Call specific reindexing if available
        if (itemType === 'sense' && typeof reindexSenses === 'function') {
            reindexSenses();
        } else if (itemType === 'pronunciation' && window.pronunciationFormsManager) {
            window.pronunciationFormsManager.reindexPronunciations();
        }
    }

    /**
     * Update visual numbering for an item
     * @param {HTMLElement} item - The item to update
     * @param {number} newIndex - New index (0-based)
     * @param {string} itemType - Type of item
     */
    updateVisualNumbering(item, newIndex, itemType) {
        const displayNumber = newIndex + 1;
        
        // Update headers and labels that show numbers
        item.querySelectorAll('h6, h5, h4, span, label').forEach(element => {
            const text = element.textContent;
            if (text.includes(`${itemType} `)) {
                element.textContent = text.replace(/\d+/, displayNumber);
            } else if (text.match(new RegExp(`${itemType}`, 'i'))) {
                // More flexible matching
                element.textContent = text.replace(/\d+/, displayNumber);
            }
        });
    }

    /**
     * Update form field names after reordering
     * @param {HTMLElement} item - The item to update
     * @param {number} newIndex - New index (0-based)
     * @param {string} itemType - Type of item
     */
    updateFieldNames(item, newIndex, itemType) {
        // Update input names based on item type
        const fieldPatterns = {
            'sense': /senses\[\d+\]/g,
            'pronunciation': /pronunciations\[\d+\]/g,
            'example': /examples\[\d+\]/g,
            'note': /notes\[\d+\]/g,
            'variant': /variants\[\d+\]/g,
            'etymology': /etymology\[\d+\]/g,
            'relation': /relations\[\d+\]/g
        };

        const pattern = fieldPatterns[itemType];
        if (!pattern) return;

        const replacement = `${itemType}s[${newIndex}]`;
        
        item.querySelectorAll('[name]').forEach(field => {
            const name = field.getAttribute('name');
            if (name && pattern.test(name)) {
                field.setAttribute('name', name.replace(pattern, replacement));
            }
        });
    }

    /**
     * Show success message
     * @param {string} message - Success message to display
     */
    showSuccess(message) {
        if (typeof showToast === 'function') {
            showToast(message, 'success');
        } else if (console) {
            console.log(message);
        }
    }
}

// Initialize the reordering manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.reorderingManager = new ReorderingManager();
});

// Make available globally
if (typeof window !== 'undefined') {
    window.ReorderingManager = ReorderingManager;
}
