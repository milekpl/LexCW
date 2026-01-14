# Minimal Fix for Sense Reordering Buttons

## Issue Fixed

The sense reordering buttons (up and down arrows) were not working correctly. This fix ensures that the visual numbering and data attributes are updated properly when senses are reordered.

## Changes Made

1. **Updated Move Button Handlers**:
   - Modified the event handlers for the move-sense-up and move-sense-down buttons
   - Added code to update both h6 and span elements containing "Sense" text
   - Added code to update the data-sense-index attribute on each sense

2. **Updated reindexSenses Function**:
   - Modified the function to handle both h6 and span elements
   - Kept the function simple to avoid potential performance issues

## How the Fix Works

When a sense is moved up or down:
1. The DOM elements are reordered using insertBefore
2. All sense items are selected and their visual numbering is updated
3. The data-sense-index attribute is updated to match the new order

This approach ensures that:
- The visual numbering is always correct
- The data attributes used for identifying senses are updated
- The form can be submitted with the correct order

## Testing Recommendations

1. **Basic Reordering**:
   - Test moving senses up and down
   - Verify that the sense numbers update correctly
   - Check that the data-sense-index attributes are updated

2. **Form Submission**:
   - Reorder senses and submit the form
   - Verify that the new order is preserved after saving