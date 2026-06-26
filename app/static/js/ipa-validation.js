/**
 * IPA Validation
 *
 * Provides real-time validation of IPA transcription fields.
 * Adds 'is-invalid' class for non-IPA characters and 'is-valid' for valid IPA.
 */

/**
 * Initialize IPA validation on all .ipa-input fields.
 * Called on page load and when new pronunciation fields are added.
 */
function initializeIPAValidation() {
    document.querySelectorAll('.ipa-input').forEach(function (input) {
        // Skip already-initialized fields
        if (input.dataset.ipaValidationInit === 'true') return;
        input.dataset.ipaValidationInit = 'true';

        input.addEventListener('input', function () {
            validateIpaField(input);
        });
        input.addEventListener('blur', function () {
            validateIpaField(input);
        });
        // Initial validation if field has a value
        if (input.value.trim()) {
            validateIpaField(input);
        }
    });
}

/**
 * Validate a single IPA input field.
 * Valid IPA: allows slashes, brackets, Unicode IPA characters, spaces, dots, and stress marks.
 * Invalid: numbers, most ASCII punctuation (except / [ ] . ' ˈ ˌ).
 */
function validateIpaField(input) {
    var value = input.value.trim();
    if (!value) {
        // Empty is fine — remove validation classes
        input.classList.remove('is-invalid', 'is-valid');
        return;
    }

    // IPA characters are mostly in the Unicode IPA Extensions blocks.
    // For simplicity, we check that the input doesn't contain obviously
    // non-IPA characters: digits 0-9 and common ASCII punctuation
    // (except IPA delimiters / [ ] . and stress marks ˈ ˌ).
    var invalidPattern = /[0-9!#$%&()*+,:;<=>?@\\^_`{|}~]/;
    // Check for consecutive stress marks (e.g., ˈˈ or ˌˌ or ˈˌ)
    var consecutiveStress = /[ˈˌ]{2,}/;
    // Also flag if the value looks like it's missing IPA delimiters
    // (doesn't start with / or [)
    var looksLikeIpa = /^[\/\[]/.test(value);

    if (invalidPattern.test(value) || consecutiveStress.test(value)) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
    } else if (looksLikeIpa) {
        input.classList.add('is-valid');
        input.classList.remove('is-invalid');
    } else {
        // No delimiters, no invalid chars — neutral
        input.classList.remove('is-invalid', 'is-valid');
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function () {
    initializeIPAValidation();
});
