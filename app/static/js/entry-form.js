/**
 * Entry Form JavaScript
 *
 * Handles dynamic form fields for dictionary entries including:
 * - Multilingual lexical units
 * - Multiple senses with definitions, glosses, and examples
 * - Pronunciations
 * - Variants
 * - Relations
 * - Etymology
 * - Annotations
 *
 * Refactored and bug-fixed version.
 *
 * FIX 2026-01-31: addSense() now uses maxIndex+1 instead of length
 * FIX 2026-01-31: reindexSenses() excludes default-sense-template
 */

// NOTE: showToast() is now provided by ui/toast.js - loaded before this file
const normalizeIndexedArray =
  window.normalizeIndexedArray ||
  function (value) {
    if (value === undefined || value === null) {
      return [];
    }

    if (Array.isArray(value)) {
      return value;
    }

    if (typeof value === "object") {
      const entries = Object.entries(value)
        .filter(
          ([key]) =>
            key !== "__proto__" &&
            key !== "constructor" &&
            key !== "prototype" &&
            !Number.isNaN(Number(key))
        )
        .sort((a, b) => Number(a[0]) - Number(b[0]));

      return entries.map(([, val]) => val);
    }

    return [];
  };

if (!window.normalizeIndexedArray) {
  window.normalizeIndexedArray = normalizeIndexedArray;
}

// Helper to apply sense relations from current DOM to formData, clearing stale values
const applySenseRelationsFromDom =
  window.applySenseRelationsFromDom ||
  function (form, formData, normalizeFn) {
    const normalize =
      typeof normalizeFn === "function" ? normalizeFn : normalizeIndexedArray;
    const result = formData || {};
    result.senses = normalize(result.senses);

    // CRITICAL: Exclude the default-sense-template to avoid adding ghost senses
    // The template should never be included in the actual data being submitted
    const senseItems = form
      ? form.querySelectorAll(
          "#senses-container .sense-item:not(#default-sense-template):not(.default-sense-template)"
        )
      : [];
    senseItems.forEach((senseEl, fallbackIndex) => {
      const senseIndex = senseEl.dataset.senseIndex;
      const idx = Number.isNaN(Number(senseIndex))
        ? fallbackIndex
        : Number(senseIndex);

      if (!result.senses[idx]) {
        result.senses[idx] = {};
      }

      const relations = [];
      senseEl
        .querySelectorAll(".sense-relation-item")
        .forEach((relEl, relIdx) => {
          const typeEl = relEl.querySelector(".sense-lexical-relation-select");
          const refEl = relEl.querySelector(".sense-relation-ref-hidden");
          const type = typeEl ? (typeEl.value || "").trim() : "";
          const ref = refEl ? (refEl.value || "").trim() : "";
          if (type || ref) {
            relations.push({ type, ref, order: relIdx });
          }
        });

      // Always set relations to the current DOM state to avoid stale data
      result.senses[idx].relations = relations;
    });

    return result;
  };

if (!window.applySenseRelationsFromDom) {
  window.applySenseRelationsFromDom = applySenseRelationsFromDom;
}

// Initialize on DOMContentLoaded or immediately if already loaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeEntryForm);
} else {
  // DOM already loaded, initialize immediately
  initializeEntryForm();
}

// Extract initialization logic into a named function to avoid double-execution
// when script is loaded after DOMContentLoaded has fired
function initializeEntryForm() {
  // REFACTOR: Define frequently used elements once to avoid repeated DOM queries.
  const sensesContainer = document.getElementById("senses-container");
  const entryForm = document.getElementById("entry-form");

  // Initialize external components if they exist
  window.rangesLoader = window.rangesLoader || new RangesLoader();

  // Initialize LIFT XML Serializer
  if (typeof LIFTXMLSerializer !== "undefined") {
    window.xmlSerializer = new LIFTXMLSerializer();
  } else {
    console.warn("[Entry Form] LIFT XML Serializer not available");
  }

  // XML Preview Toggle Handler
  const xmlPreviewPanel = document.getElementById("xml-preview-panel");
  const toggleXmlPreviewBtn = document.getElementById("toggle-xml-preview-btn");
  const copyXmlBtn = document.getElementById("copy-xml-btn");
  const xmlPreviewContent = document.getElementById("xml-preview-content");

  if (toggleXmlPreviewBtn && xmlPreviewPanel) {
    toggleXmlPreviewBtn.addEventListener("click", function () {
      if (xmlPreviewPanel.style.display === "none") {
        // Show panel and generate XML
        xmlPreviewPanel.style.display = "block";
        updateXmlPreview();
        toggleXmlPreviewBtn.innerHTML =
          '<i class="fas fa-code-slash"></i> Hide XML';
      } else {
        // Hide panel
        xmlPreviewPanel.style.display = "none";
        toggleXmlPreviewBtn.innerHTML =
          '<i class="fas fa-code"></i> XML Preview';
      }
    });
  }

  // Copy XML to clipboard
  if (copyXmlBtn && xmlPreviewContent) {
    copyXmlBtn.addEventListener("click", function () {
      const xmlText = xmlPreviewContent.textContent;
      navigator.clipboard
        .writeText(xmlText)
        .then(() => {
          showToast("XML copied to clipboard", "success");
        })
        .catch((err) => {
          console.error("Failed to copy XML:", err);
          showToast("Failed to copy XML", "error");
        });
    });
  }

  /**
   * Update XML Preview with current form data
   */
  function updateXmlPreview() {
    if (!window.xmlSerializer || !xmlPreviewContent) return;

    try {
      // Build the serializer input via the shared helper: legacy DOM merged with all
      // Alpine-owned sections (lexical-unit, senses, relations, etc. have no name= inputs).
      // Using the legacy serializer alone yields an empty lexicalUnit -> "must have at
      // least one form".
      // All sections are Alpine-owned (§16.3 B2); buildSerializerInput is the sole path.
      let formData = window.MergeHarness
        ? window.MergeHarness.buildSerializerInput(entryForm, { includeEmpty: true })
        : {};

      // A brand-new entry (add page) has id=""; give the preview a temporary id so the
      // serializer (which requires an id) can render it — mirrors the submit path.
      if (!formData.id) {
        formData.id =
          (window.xmlSerializer.generateEntryId &&
            window.xmlSerializer.generateEntryId()) ||
          `temp-${Date.now()}`;
      }

      // Generate XML directly from form data (serializer now handles snake_case)
      const xmlString = window.xmlSerializer.serializeEntry(formData);

      // Display in preview panel
      xmlPreviewContent.textContent = xmlString;

      // Highlight syntax (optional - could add a lightweight highlighter later)
    } catch (error) {
      console.error("[XML Preview] Error generating XML:", error);
      console.error("[XML Preview] Error stack:", error.stack);
      xmlPreviewContent.textContent = `Error generating XML: ${error.message}\n\nCheck browser console (F12) for details.`;
    }
  }

  // Expose for other modules (relations search, etc.) to trigger refresh
  window.updateXmlPreview = updateXmlPreview;

  /**
   * Function to initialize dynamic selects.
   * Populates select elements with options from a given range.
   */
  async function initializeDynamicSelects(container) {
    // Initialize grammatical-info selects
    const dynamicSelects = container.querySelectorAll(
      ".dynamic-grammatical-info"
    );

    const promises = Array.from(dynamicSelects).map((select) => {
      const rangeId = select.dataset.rangeId;
      const selectedValue = select.dataset.selected;
      if (rangeId) {
        // Assuming populateSelect is an async function that returns a promise
        return window.rangesLoader.populateSelect(select, rangeId, {
          selectedValue: selectedValue,
          emptyOption: "Select part of speech",
        });
      }
      return Promise.resolve(); // Return a resolved promise for selects without a rangeId
    });

    // Initialize ALL dynamic-lift-range selects (semantic-domain, usage-type, etc.)
    const allDynamicRanges = container.querySelectorAll(".dynamic-lift-range");

    const rangePromises = Array.from(allDynamicRanges).map((select) => {
      const rangeId = select.dataset.rangeId;
      const selectedValue = select.dataset.selected;
      const hierarchical = select.dataset.hierarchical === "true";
      const searchable = select.dataset.searchable === "true";

      if (rangeId && window.rangesLoader) {
        return window.rangesLoader
          .populateSelect(select, rangeId, {
            selectedValue: selectedValue,
            emptyOption:
              select.querySelector('option[value=""]')?.textContent ||
              "Select option",
            hierarchical: hierarchical,
            searchable: searchable,
          })
          .catch((err) => {
            console.error(`[Entry Form] Failed to populate ${rangeId}:`, err);
          });
      }
      return Promise.resolve();
    });

    await Promise.all([...promises, ...rangePromises]);
  }

  /**
   * Grammatical Category Inheritance Logic.
   * Automatically derives and validates the entry-level grammatical category
   * based on the categories of its senses, as per specification 7.2.1.
   */
  async function updateGrammaticalCategoryInheritance() {
    const entryPartOfSpeechSelect = document.getElementById("part-of-speech");
    const requiredIndicator = document.getElementById("pos-required-indicator");
    if (!entryPartOfSpeechSelect) return;

    // Sense POS now lives in the Alpine senseTree (sense.grammaticalInfo) — the sense
    // Part of Speech is a searchable combobox, not a DOM <select>. Read from Alpine.
    let senseCategories = [];
    const senseTreeEl = document.querySelector('[x-data^="senseTree"]');
    if (senseTreeEl && window.Alpine) {
      try {
        const stData = window.Alpine.$data(senseTreeEl);
        senseCategories = (stData.senses || [])
          .map((s) => s.grammaticalInfo)
          .filter((value) => value && value.trim());
      } catch (e) {
        /* Alpine not ready yet — nothing to inherit */
      }
    }

    // REFACTOR: Clear existing validation state more robustly.
    entryPartOfSpeechSelect.classList.remove("is-invalid", "is-valid");
    const feedbackElement = entryPartOfSpeechSelect.parentElement.querySelector(
      ".invalid-feedback, .valid-feedback"
    );
    if (feedbackElement) {
      feedbackElement.remove();
    }

    if (senseCategories.length === 0) {
      // No senses have a part of speech selected. The entry-level field is optional.
      entryPartOfSpeechSelect.required = false;
      if (requiredIndicator) requiredIndicator.style.display = "none";
      return;
    }

    const uniqueCategories = [...new Set(senseCategories)];

    if (uniqueCategories.length === 1) {
      // All senses agree. Auto-inherit the category. Entry POS is owned by the Alpine
      // entryMeta component (x-model="grammaticalInfo"), so set it there — a raw
      // `.value =` would not sync back into Alpine state and would be lost on save.
      const commonCategory = uniqueCategories[0];
      const entryMetaEl = document.querySelector('[x-data^="entryMeta"]');
      if (entryMetaEl && window.Alpine) {
        try { window.Alpine.$data(entryMetaEl).grammaticalInfo = commonCategory; } catch (e) { /* ignore */ }
      } else {
        entryPartOfSpeechSelect.value = commonCategory;
      }
      entryPartOfSpeechSelect.required = false;
      if (requiredIndicator) requiredIndicator.style.display = "none";

      entryPartOfSpeechSelect.classList.add("is-valid");
      const feedback = document.createElement("div");
      feedback.className = "valid-feedback";
      feedback.textContent = "Automatically inherited from senses.";
      entryPartOfSpeechSelect.parentElement.appendChild(feedback);
    } else {
      // Discrepancy detected. Field is required, show an error.
      entryPartOfSpeechSelect.required = true;
      if (requiredIndicator) requiredIndicator.style.display = "inline";
      entryPartOfSpeechSelect.classList.add("is-invalid");
      const feedback = document.createElement("div");
      feedback.className = "invalid-feedback";
      feedback.innerHTML = `
                <strong>Grammatical category discrepancy detected!</strong><br>
                Senses have different categories: ${uniqueCategories.join(
                  ", "
                )}.<br>
                Please manually select the correct entry-level category.
            `;
      entryPartOfSpeechSelect.parentElement.appendChild(feedback);
    }
  }

  /**
   * Propagate entry-level POS to senses that don't have a POS set.
   * Called when user changes the entry-level #part-of-speech select.
   */
  function propagatePosToSenses() {
    const entryPosSelect = document.getElementById("part-of-speech");
    if (!entryPosSelect) return;

    const entryPos = entryPosSelect.value;
    if (!entryPos) return; // Don't propagate empty values

    // Delegate to the Alpine senseTree component (§11.4).
    // applyEntryPos only overwrites senses whose grammaticalInfo is empty —
    // preserving any sense-level POS the user set explicitly.
    const el = document.querySelector('[x-data^="senseTree"]');
    if (el && window.Alpine) {
      window.Alpine.$data(el).applyEntryPos(entryPos);
    }

    // After propagation, update inheritance state to reflect new sense values.
    // Alpine updates the DOM via microtask, so wait one tick before reading it.
    Promise.resolve().then(function () {
      updateGrammaticalCategoryInheritance();
    });
  }

  /**
   * Sets up event listeners for the grammatical category inheritance logic.
   */
  function setupGrammaticalInheritanceListeners() {
    // Listen for changes in any sense's grammatical category select.
    // Using event delegation on the form for efficiency.
    if (entryForm) {
      entryForm.addEventListener("change", function (e) {
        if (e.target.matches("#senses-container .dynamic-grammatical-info")) {
          updateGrammaticalCategoryInheritance();
        }
        // Listen for entry-level POS changes and propagate to senses
        if (e.target.id === "part-of-speech") {
          propagatePosToSenses();
        }
      });
    }

    // Use a MutationObserver to detect when senses are added or removed.
    if (sensesContainer) {
      // REFACTOR: The observer is simplified. Explicit calls after add/remove
      // are more reliable, but this observer catches all list changes.
      // We only need to observe direct children additions/removals.
      const observer = new MutationObserver(() => {
        updateGrammaticalCategoryInheritance();
      });
      observer.observe(sensesContainer, {
        childList: true,
      });
    }
  }

  // --- Initialization Sequence ---

  function initializeMergeSplitButtons() {
    document
      .getElementById("merge-senses-btn")
      ?.addEventListener("click", function (e) {
        e.preventDefault();
        const entryId = document.querySelector('input[name="id"]')?.value;
        openMergeSensesDialog(entryId);
      });

    document
      .getElementById("senses-container")
      ?.addEventListener("click", function (e) {
        const splitBtn = e.target.closest(".split-sense-btn");
        if (splitBtn) {
          e.preventDefault();
          const senseId = splitBtn.dataset.senseId;
          const entryId = document.querySelector('input[name="id"]')?.value;
          openSplitEntryDialog(entryId, [senseId]);
        }
      });
  }

  function openMergeSensesDialog(entryId) {
    const mergeSensesModalEl = document.getElementById("mergeSensesModal");
    const mergeSensesModal = new bootstrap.Modal(mergeSensesModalEl);
    const targetSenseSelect =
      mergeSensesModalEl.querySelector("#targetSenseSelect");
    const sourceSensesList =
      mergeSensesModalEl.querySelector("#sourceSensesList");

    targetSenseSelect.innerHTML =
      '<option value="">Select target sense...</option>';
    sourceSensesList.innerHTML = "";

    const senseItems = document.querySelectorAll(
      "#senses-container .sense-item"
    );
    const senses = Array.from(senseItems).map((item) => {
      const id = item.querySelector('input[name*=".id"]')?.value;
      const gloss = item.querySelector('textarea[name*=".definition."]')?.value; // using definition as a stand-in for gloss
      return {
        id,
        gloss: gloss ? gloss.substring(0, 50) + "..." : `Sense ${id}`,
      };
    });

    if (senses.length < 2) {
      alert("You need at least two senses to merge.");
      return;
    }

    senses.forEach((sense) => {
      const option = document.createElement("option");
      option.value = sense.id;
      option.textContent = sense.gloss;
      targetSenseSelect.appendChild(option);
    });

    targetSenseSelect.addEventListener("change", () => {
      const targetId = targetSenseSelect.value;
      sourceSensesList.innerHTML = "";
      senses.forEach((sense) => {
        if (sense.id !== targetId) {
          const item = document.createElement("div");
          item.className = "list-group-item";
          item.innerHTML = `
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="${sense.id}" id="merge-source-sense-${sense.id}">
                            <label class="form-check-label" for="merge-source-sense-${sense.id}">
                                ${sense.gloss}
                            </label>
                        </div>
                    `;
          sourceSensesList.appendChild(item);
        }
      });
    });

    mergeSensesModal.show();
  }

  const confirmMergeSensesBtn = document.getElementById("confirmMergeSenses");
  if (confirmMergeSensesBtn) {
    confirmMergeSensesBtn.addEventListener("click", () => {
      const mergeSensesModalEl = document.getElementById("mergeSensesModal");
      const entryId = document.querySelector('input[name="id"]').value;
      const targetSenseId =
        mergeSensesModalEl.querySelector("#targetSenseSelect").value;
      const sourceSenseIds = Array.from(
        mergeSensesModalEl.querySelectorAll("#sourceSensesList input:checked")
      ).map((input) => input.value);
      const mergeStrategy = mergeSensesModalEl.querySelector(
        'input[name="mergeStrategy"]:checked'
      ).value;

      if (!targetSenseId) {
        alert("Please select a target sense.");
        return;
      }
      if (sourceSenseIds.length === 0) {
        alert("Please select at least one source sense.");
        return;
      }

      const payload = {
        source_sense_ids: sourceSenseIds,
        merge_strategy: mergeStrategy,
      };

      // Get CSRF token
      const headers = getCsrfHeaders({ "Content-Type": "application/json" });

      fetch(
        `/api/merge-split/entries/${entryId}/senses/${targetSenseId}/merge`,
        {
          method: "POST",
          headers: headers,
          body: JSON.stringify(payload),
        }
      )
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            showToast("Senses merged successfully!", "success");
            const mergeSensesModal =
              bootstrap.Modal.getInstance(mergeSensesModalEl);
            mergeSensesModal.hide();
            location.reload(); // Easiest way to show the result
          } else {
            alert(`Error merging senses: ${data.error}`);
          }
        })
        .catch((error) => {
          console.error("Error merging senses:", error);
          alert("An error occurred while merging senses.");
        });
    });
  }

  function openSplitEntryDialog(entryId, senseIds) {
    const splitEntryModal = new bootstrap.Modal(
      document.getElementById("splitEntryModal")
    );
    splitEntryModal.show();
    document.getElementById("splitSourceEntry").textContent = entryId;
  }

  // Expose the update function globally for other components that might add senses.
  window.updateGrammaticalCategoryInheritance =
    updateGrammaticalCategoryInheritance;

  // 1. Initialize all dynamic select elements on the page.
  initializeDynamicSelects(document.body).then(() => {
    // 2. After selects are populated, set up the inheritance logic.
    setupGrammaticalInheritanceListeners();

    // 3. Run an initial check on the grammatical inheritance.
    // REFACTOR: Removed unreliable setTimeout. This now runs after selects are ready.
    updateGrammaticalCategoryInheritance();
  });

  initializeMergeSplitButtons();

  // Initialize Select2 for any tag inputs.
  $(".select2-tags").select2({
    theme: "bootstrap-5",
    tags: true,
    tokenSeparators: [",", " "],
    placeholder: "Enter or select values...",
  });

  // --- Main Event Handlers ---

  // --- Main Event Handlers ---

  if (entryForm) {
    entryForm.addEventListener("submit", function (e) {
      e.preventDefault();

      // Ensure sense indices and field names are consistent before serialization.
      // This prevents duplicate `senses[N]...` field names after add/delete/reorder.
      try {
        if (typeof reindexSenses === "function") {
          reindexSenses();
        }
      } catch (err) {
        console.warn("[Entry Form] Failed to reindex senses before submit:", err);
      }

      // Check if user wants to skip validation
      const skipValidationCheckbox = document.getElementById(
        "skip-validation-checkbox"
      );
      const shouldSkipValidation =
        skipValidationCheckbox && skipValidationCheckbox.checked;

      if (shouldSkipValidation) {
        // Skip validation and submit directly
        submitForm();
      } else {
        // Submit form - validation will happen server-side
        submitForm();
      }
    });
  }

  const validateBtn = document.getElementById("validate-btn");
  if (validateBtn) {
    validateBtn.addEventListener("click", () => {
      validateForm(true);
    });
  } else {
    console.warn("[Entry Form] Validate button not found");
  }

  document.getElementById("cancel-btn")?.addEventListener("click", () => {
    if (
      confirm(
        "Are you sure you want to cancel? Any unsaved changes will be lost."
      )
    ) {
      window.location.href = "/entries";
    }
  });

  document
    .getElementById("add-pronunciation-btn")
    ?.addEventListener("click", addPronunciation);
  document.getElementById("add-sense-btn")?.addEventListener("click", addSense);
  document
    .getElementById("add-first-sense-btn")
    ?.addEventListener("click", function () {
      document.getElementById("no-senses-message")?.remove();
      addSense();
    });

  // STAGE 2.1: Lexical-unit forms now managed by Alpine — legacy handlers are no-ops

  // --- Event Delegation for Dynamic Elements ---

  document
    .getElementById("pronunciation-container")
    ?.addEventListener("click", function (e) {
      // STAGE 2.2: Pronunciation remove is now handled by Alpine @click — skip legacy handler
      const removeBtn = e.target.closest(".remove-pronunciation-btn");
      if (removeBtn) {
        return; // Alpine handles removal via splice on the items array
      }

      const uploadBtn = e.target.closest(".upload-audio-btn");
      if (uploadBtn) {
        const index = uploadBtn.dataset.index;
        const fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.accept = "audio/*";

        fileInput.onchange = async (event) => {
          const file = event.target.files[0];
          if (!file) return;

          const pronunciationItem = uploadBtn.closest(".pronunciation-item");
          const ipaInput = pronunciationItem.querySelector(".ipa-input");
          const audioPathInput = pronunciationItem.querySelector(
            'input[name*="audio_path"]'
          );
          const ipaValue = ipaInput ? ipaInput.value.trim() : "";

          // Validate IPA is provided (required by API)
          if (!ipaValue) {
            alert("Please enter an IPA transcription before uploading audio.");
            // Clean up file input
            if (document.body.contains(fileInput)) {
              document.body.removeChild(fileInput);
            }
            return;
          }

          // Show loading state
          const originalText = uploadBtn.innerHTML;
          uploadBtn.innerHTML =
            '<i class="fas fa-spinner fa-spin"></i> Uploading...';
          uploadBtn.disabled = true;

          try {
            const formData = new FormData();
            formData.append("audio_file", file);
            formData.append("ipa_value", ipaValue);
            formData.append("index", index);

            const response = await fetch("/api/pronunciation/upload", {
              method: "POST",
              body: formData,
            });

            const result = await response.json();

            if (response.ok && result.success) {
              // Update the hidden input with the filename
              audioPathInput.value = result.filename;

              // Show success
              uploadBtn.innerHTML = '<i class="fas fa-check"></i> Uploaded';

              // Add audio preview if audio player exists
              const audioPlayer = pronunciationItem.querySelector("audio");
              if (audioPlayer) {
                audioPlayer.src = `/static/audio/${result.filename}`;
                audioPlayer.style.display = "block";
              }

              setTimeout(() => {
                uploadBtn.innerHTML = originalText;
                uploadBtn.disabled = false;
              }, 2000);
            } else {
              throw new Error(result.message || "Upload failed");
            }
          } catch (error) {
            console.error("Audio upload error:", error);
            alert("Failed to upload audio: " + error.message);
            uploadBtn.innerHTML = originalText;
            uploadBtn.disabled = false;
          }

          // Clean up file input
          if (document.body.contains(fileInput)) {
            document.body.removeChild(fileInput);
          }
        };

        fileInput.click();
        return;
      }

      const generateBtn = e.target.closest(".generate-audio-btn");
      if (generateBtn) {
        const pronunciationItem = generateBtn.closest(".pronunciation-item");
        const ipaInput = pronunciationItem.querySelector(".ipa-input");
        const lexicalUnit = document.getElementById("lexical-unit").value;

        // Allow generation even without IPA - will use word text for TTS
        const ipaValue = ipaInput ? ipaInput.value.trim() : "";
        generateAudio(lexicalUnit, ipaValue, generateBtn.dataset.index);
      }
    });


  // --- Audio Modal Handling ---
  const audioPreviewModalEl = document.getElementById("audioPreviewModal");
  const audioPreviewModal = audioPreviewModalEl
    ? new bootstrap.Modal(audioPreviewModalEl)
    : null;

  document
    .getElementById("save-audio-btn")
    ?.addEventListener("click", function () {
      const audioPlayer = document.getElementById("audio-preview-player");
      const audioSrc = audioPlayer.src;
      const index = audioPlayer.dataset.pronunciationIndex;
      const audioFileInput = document.querySelector(
        `input[name="pronunciations[${index}].audio_file"]`
      );

      if (audioFileInput) {
        // Assuming the URL path contains the filename we want to save.
        audioFileInput.value = audioSrc.split("/").pop();
      }
      audioPreviewModal?.hide();
    });
}

/**
 * Validates the entire form, highlighting errors and optionally showing a summary modal.
 * @param {boolean} showSummaryModal - If true, displays a modal with a list of validation errors.
 * @returns {boolean} - True if the form is valid, false otherwise.
 */
function validateForm(showSummaryModal = false) {
  const errors = [];
  let isValid = true;

  // Helper to invalidate a field and add an error message
  const invalidate = (element, message) => {
    if (element) {
      element.classList.add("is-invalid");
      const feedback =
        element.parentElement.querySelector(".invalid-feedback") ||
        document.createElement("div");
      feedback.className = "invalid-feedback";
      feedback.textContent = message;
      if (!feedback.parentElement) {
        element.parentElement.appendChild(feedback);
      }
    }
    errors.push(message);
    isValid = false;
  };

  // Clear previous validation
  document
    .querySelectorAll(".is-invalid")
    .forEach((el) => el.classList.remove("is-invalid"));

  // Validate Lexical Unit (check all language inputs, at least one must have a value)
  const lexicalUnitInputs = document.querySelectorAll(".lexical-unit-text");
  const hasLexicalUnit = Array.from(lexicalUnitInputs).some((input) =>
    input.value.trim()
  );
  if (!hasLexicalUnit && lexicalUnitInputs.length > 0) {
    // Mark the first input as invalid
    invalidate(
      lexicalUnitInputs[0],
      "Lexical Unit is required in at least one language."
    );
  }

  // Validate Part of Speech (only if required by inheritance logic)
  const partOfSpeechEl = document.getElementById("part-of-speech");
  if (partOfSpeechEl && partOfSpeechEl.required && !partOfSpeechEl.value) {
    invalidate(
      partOfSpeechEl,
      "Part of Speech is required due to sense discrepancies."
    );
  }

  // Validate Senses
  const senses = document.querySelectorAll(".sense-item");
  if (senses.length === 0) {
    errors.push("At least one sense is required.");
    isValid = false;
    // Visually indicate the error on the senses container or a related element
    document
      .getElementById("senses-section-header")
      ?.classList.add("text-danger");
  } else {
    document
      .getElementById("senses-section-header")
      ?.classList.remove("text-danger");

    senses.forEach((sense, index) => {
      // Check for multilingual definition fields
      const definitionForms = sense.querySelectorAll(
        ".definition-forms .language-form"
      );
      let hasValidDefinition = false;

      if (definitionForms.length > 0) {
        // Check each language form for a valid definition
        // IMPORTANT: Source language definitions are COMPLETELY OPTIONAL!
        // We just need ANY language with content
        definitionForms.forEach((form) => {
          const textareaEl = form.querySelector(".definition-text");

          // Check if ANY language has content (source or target)
          if (textareaEl && textareaEl.value.trim()) {
            hasValidDefinition = true;
          }
        });

        // If no valid definition found, mark the first textarea as invalid
        if (!hasValidDefinition) {
          const firstTextarea = sense.querySelector(
            ".definition-forms .language-form:first-child .definition-text"
          );
          if (firstTextarea) {
            invalidate(
              firstTextarea,
              `Sense ${
                index + 1
              }: Definition is required in at least one language.`
            );
          } else {
            errors.push(
              `Sense ${
                index + 1
              }: Definition is required in at least one language.`
            );
            isValid = false;
          }
        }
      } else {
        // Fallback to old structure (should not happen with updated template)
        const definitionEl = sense.querySelector(
          `textarea[name="senses[${index}].definition"]`
        );
        if (definitionEl && !definitionEl.value.trim()) {
          invalidate(
            definitionEl,
            `Sense ${index + 1}: Definition is required.`
          );
        } else if (!definitionEl) {
          errors.push(`Sense ${index + 1}: Definition field not found.`);
          isValid = false;
        }
      }

      // Validate Examples
      sense.querySelectorAll(".example-item").forEach((example, exIndex) => {
        const exampleTextEl = example.querySelector(
          `textarea[name*="examples"][name*="sentence"]`
        );
        if (exampleTextEl && !exampleTextEl.value.trim()) {
          invalidate(
            exampleTextEl,
            `Sense ${index + 1}, Example ${
              exIndex + 1
            }: Example text is required.`
          );
        }
      });
    });
  }

  // Show summary if requested
  if (showSummaryModal) {
    if (!isValid) {
      // Form has errors - show them in modal for detailed review
      const errorsList = document.getElementById("validation-errors-list");
      const validationModalEl = document.getElementById("validationModal");

      if (!validationModalEl) {
        console.error("[validateForm] validationModal element not found");
        showToast(
          `Form has ${errors.length} validation error(s). Check the form for details.`,
          "error"
        );
        return isValid;
      }

      if (errorsList) {
        errorsList.innerHTML = errors
          .map((error) => `<li class="text-danger">${error}</li>`)
          .join("");
        const modalHeader = validationModalEl.querySelector(".modal-header");
        const modalTitle = validationModalEl.querySelector(".modal-title");
        if (modalHeader)
          modalHeader.className = "modal-header bg-danger text-white";
        if (modalTitle) modalTitle.textContent = "Validation Errors";
        const validationModal = new bootstrap.Modal(validationModalEl);
        validationModal.show();
      } else {
        console.error(
          "[validateForm] validation-errors-list element not found"
        );
        showToast(
          `Form has ${errors.length} validation error(s). Check the form for details.`,
          "error"
        );
      }
    } else {
      // Form is valid - show unobtrusive success toast
      showToast("✓ Form validation passed! No errors found.", "success");
    }
  }

  return isValid;
}

/**
 * Serializes and submits the form data via AJAX with improved error handling.
 * Now uses LIFT XML serialization instead of JSON.
 */
async function submitForm() {
  const form = document.getElementById("entry-form");
  if (!form) {
    console.error("Form not found");
    return;
  }

  // STAGE 1: Senses are now Alpine-managed; reindexSenses is a no-op.
  // Sense ordering is maintained reactively by the Alpine senseTree component.
  try {
    reindexSenses();
  } catch (err) {
    console.warn("[Entry Form] Failed to reindex senses before save:", err);
  }

  const saveBtn = document.getElementById("save-btn");
  const originalText = saveBtn.innerHTML;
  saveBtn.innerHTML =
    '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
  saveBtn.disabled = true;

  // Add a progress indicator
  const progressContainer = document.createElement("div");
  progressContainer.className = "progress mt-2";
  progressContainer.innerHTML =
    '<div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>';
  saveBtn.parentNode.appendChild(progressContainer);
  const progressBar = progressContainer.querySelector(".progress-bar");

  try {
    // Update progress
    progressBar.style.width = "10%";
    progressBar.textContent = "Preparing data...";

    // Check if XML serializer is available
    if (!window.xmlSerializer) {
      throw new Error("LIFT XML Serializer is not loaded.");
    }

    // DEBUG: Log all sense-related field names before serialization
    const allSenseFields = form.querySelectorAll('[name*="senses["]');
    const fieldNameCounts = {};
    allSenseFields.forEach((field) => {
      const name = field.name;
      fieldNameCounts[name] = (fieldNameCounts[name] || 0) + 1;
    });
    const duplicates = Object.entries(fieldNameCounts).filter(
      ([name, count]) => count > 1
    );
    if (duplicates.length > 0) {
      console.error("[SAVE ENTRY] DUPLICATE FIELD NAMES DETECTED:", duplicates);
    }
    console.log(
      `[SAVE ENTRY] Total sense fields: ${allSenseFields.length}, Unique: ${
        Object.keys(fieldNameCounts).length
      }`
    );

    // All sections are Alpine-owned (§16.3 B2). Build serializer input from Alpine state only.
    var formData = {};
    if (window.MergeHarness) {
      formData = window.MergeHarness.buildSerializerInput(form);
    }

    // Note: gloss→glosses conversion is handled by the Alpine adapter
    // (alpine-to-serializer.js emits `glosses` directly). No post-processing needed here.

    // Update progress
    progressBar.style.width = "30%";
    progressBar.textContent = "Generating LIFT XML...";

    // Ensure formData has an id so older/cached serializers don't throw
    if (!formData.id) {
      let tempId;
      if (
        window.xmlSerializer &&
        typeof window.xmlSerializer.generateEntryId === "function"
      ) {
        try {
          tempId = window.xmlSerializer.generateEntryId();
        } catch (e) {
          tempId = null;
        }
      }
      if (!tempId) {
        tempId = `temp-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
      }
      formData.id = tempId;
      console.warn(
        `[FORM SUBMIT] No entry id in formData; assigned temporary id: ${formData.id}`
      );
    }

    // Generate LIFT XML directly from form data (serializer now handles snake_case)
    let xmlString;
    try {
      xmlString = window.xmlSerializer.serializeEntry(formData);
    } catch (xmlError) {
      throw new Error(`XML generation failed: ${xmlError.message}`);
    }

    // Validate XML if needed
    const skipValidationCheckbox = document.getElementById(
      "skip-validation-checkbox"
    );
    const skipValidation =
      skipValidationCheckbox && skipValidationCheckbox.checked;

    // Update progress
    progressBar.style.width = "50%";
    progressBar.textContent = "Sending to server...";

    const entryId = form.querySelector('input[name="id"]')?.value?.trim();
    const apiUrl = entryId ? `/api/xml/entries/${entryId}` : "/api/xml/entries";
    const apiMethod = entryId ? "PUT" : "POST";

    // Debug: Log sense count in XML being sent
    const senseMatchesBefore = xmlString.match(/<sense\s+/g);
    const senseCountBefore = senseMatchesBefore ? senseMatchesBefore.length : 0;

    // If E2E capture is enabled, expose the serialized XML to the page context
    // This is a temporary debug hook for end-to-end tests to assert the outgoing body
    // It will be removed once the issue is diagnosed and fixed.
    if (window.__E2E_CAPTURE_XML) {
      try {
        // Full XML is stored for test inspection
        window.__LAST_SERIALIZED_XML = xmlString;
        // Log a short marker and length for easier capture in console logs
        console.log("E2E: SERIALIZED_XML_LENGTH", xmlString.length);
        console.log("E2E: SERIALIZED_XML_SNIPPET", xmlString.slice(0, 1000));
      } catch (e) {
        console.warn("E2E capture failed", e);
      }
    }

    // Set a timeout for the fetch request
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout

    // Get CSRF token
    const headers = getCsrfHeaders({
      "Content-Type": "application/xml",
      Accept: "application/json",
    });

    const response = await fetch(apiUrl, {
      method: apiMethod,
      headers: headers,
      body: xmlString,
      signal: controller.signal,
    });

    // Clear the timeout
    clearTimeout(timeoutId);

    // Update progress
    progressBar.style.width = "80%";
    progressBar.textContent = "Processing response...";

    const responseData = await response.json();

    if (!response.ok) {
      // Handle validation errors from server
      if (
        responseData.validation_errors &&
        Array.isArray(responseData.validation_errors)
      ) {
        // Display structured validation errors
        const errorList = responseData.validation_errors
          .map((err) => `• ${err}`)
          .join("\n");
        throw new Error(`Validation failed:\n${errorList}`);
      } else {
        // Extract a more detailed error message if available
        const errorMessage =
          responseData.error ||
          responseData.message ||
          `HTTP error! Status: ${response.status}`;
        throw new Error(errorMessage);
      }
    }

    // Update progress
    progressBar.style.width = "100%";
    progressBar.textContent = "Complete!";

    // Save revision snapshot (XHR with CSRF headers — completes before redirect)
    const idForRevision = responseData.entry_id || entryId;
    if (idForRevision) {
      try {
        var snapshot = window.MergeHarness ? window.MergeHarness.buildSerializerInput(form) : null;
        if (!snapshot || Object.keys(snapshot).length === 0) snapshot = formData;
        if (snapshot) {
          snapshot.id = idForRevision;
          var revHeaders = (typeof getCsrfHeaders === 'function')
            ? getCsrfHeaders({ 'Content-Type': 'application/json' })
            : { 'Content-Type': 'application/json' };
          // Fallback: read from meta tag if getCsrfHeaders is unavailable
          if (!revHeaders['X-CSRF-TOKEN'] && !revHeaders['X-CSRFToken']) {
            var meta = document.querySelector('meta[name="csrf-token"]');
            if (meta) revHeaders['X-CSRF-TOKEN'] = meta.getAttribute('content');
          }
          var xhr = new XMLHttpRequest();
          xhr.open('POST', '/api/entries/' + encodeURIComponent(idForRevision) + '/revisions', false);
          Object.keys(revHeaders).forEach(function (k) { xhr.setRequestHeader(k, revHeaders[k]); });
          xhr.send(JSON.stringify({ snapshot: snapshot }));
        }
      } catch (e) { /* best-effort */ }
    }

    // Redirect after successful save
    const idForRedirect = idForRevision;
    if (idForRedirect) {
      window.location.href = `/entries/${idForRedirect}?status=saved`;
    } else {
      console.warn(
        "No entry ID found for redirect. Redirecting to entries list."
      );
      window.location.href = "/entries";
    }
  } catch (error) {
    console.error("Submission Error:", error);
    saveBtn.innerHTML = originalText;
    saveBtn.disabled = false;

    // Update progress to show error
    progressBar.style.width = "100%";
    progressBar.className = "progress-bar bg-danger";
    progressBar.textContent = "Error!";

    // Show detailed error message (preserve newlines in toast)
    const errorDiv = document.createElement("div");
    errorDiv.style.whiteSpace = "pre-wrap";
    errorDiv.textContent = error.message;
    showToast(
      errorDiv.innerHTML || `Error saving entry: ${error.message}`,
      "error"
    );

    // Remove progress bar after delay
    setTimeout(() => {
      progressContainer.remove();
    }, 5000);
  }
}

// --- Dynamic Element Creation Functions ---

/**
 * Adds a new pronunciation field group to the form.
 * 
 * STAGE 2.2 (Alpine migration): No-op. Pronunciation management is handled by the Alpine
 * pronunciation component. Will be deleted in Stage 3.
 */
function addPronunciation() {
  console.debug("[addPronunciation] Stage 2.2: pronunciations now managed by Alpine — no-op");
}

/**
 * Adds a new sense field group to the form.
 * 
 * STAGE 1 (Alpine migration): No-op. Sense management is handled by the Alpine
 * senseTree component. This function is kept as a no-op for backward compatibility
 * with callers that still reference it. Will be deleted in Stage 3.
 */
async function addSense() {
  console.debug("[addSense] Stage 1: senses now managed by Alpine senseTree component — no-op");
}

/**
 * Adds a new example field group to a specific sense.
 * 
 * STAGE 1 (Alpine migration): No-op. Example management is handled by the Alpine
 * senseTree component. This function is kept as a no-op for backward compatibility.
 * Will be deleted in Stage 3.
 */
function addExample(senseIndex) {
  console.debug("[addExample] Stage 1: examples now managed by Alpine senseTree component — no-op");
}

// STAGE 1: No-op wrapper kept for backward compatibility
window.addExampleForCorpus = function (senseIndex, sentence, translation) {
  console.debug("[addExampleForCorpus] Stage 1: examples now managed by Alpine — no-op");
};

/**
 * Handle corpusExampleSelected event from CorpusSearch.
 * Adds a new example with the selected sentence and translation.
 */
function handleCorpusExampleSelected(event) {
  const { senseIndex, sentence, translation } = event.detail;
  if (senseIndex === undefined || senseIndex === null) {
    Logger.warn("handleCorpusExampleSelected: Missing senseIndex", {
      senseIndex,
    });
    return;
  }
  window.addExampleForCorpus(senseIndex, sentence, translation);
}

// Initialize event listener for corpus example selection
document.addEventListener("corpusExampleSelected", handleCorpusExampleSelected);

/**
 * Adds a new sense relation field group to a specific sense.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function addSenseRelation(senseIndex) {
  const relationsContainer = document.querySelector(
    `.sense-relations-container[data-sense-index="${senseIndex}"]`
  );
  if (!relationsContainer) return;

  const newIndex = relationsContainer.querySelectorAll(
    ".sense-relation-item"
  ).length;
  const newNumber = newIndex + 1;

  // Create new sense relation HTML dynamically since there's no template
  const newRelationHTML = `
        <div class="sense-relation-item card mb-3 border-warning" data-relation-index="${newIndex}">
            <div class="card-header bg-warning bg-opacity-10">
                <div class="d-flex justify-content-between align-items-center">
                    <span><i class="fas fa-link"></i> Relation ${newNumber}</span>
                    <button type="button" class="btn btn-sm btn-outline-danger remove-sense-relation-btn"
                            data-sense-index="${senseIndex}" data-relation-index="${newIndex}">
                        <i class="fas fa-trash"></i> Remove
                    </button>
                </div>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <label class="form-label">Relation Type</label>
                        <select class="form-control sense-lexical-relation-select dynamic-lift-range"
                                name="senses[${senseIndex}].relations[${newIndex}].type"
                                data-range-id="lexical-relation"
                                data-hierarchical="true"
                                data-searchable="true"
                                required>
                            <option value="">Select type</option>
                        </select>
                        <div class="form-text">Type of semantic relation</div>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Target Sense</label>
                        <div class="alert alert-light mb-2">
                            <i class="fas fa-project-diagram me-2"></i>
                            <strong>No target selected</strong>
                        </div>
                        <input type="hidden"
                               class="sense-relation-ref-hidden"
                               name="senses[${senseIndex}].relations[${newIndex}].ref"
                               value="">
                        <div class="input-group">
                            <input type="text"
                                   class="form-control sense-relation-search-input"
                                   placeholder="Search to change target..."
                                   data-sense-index="${senseIndex}"
                                   data-relation-index="${newIndex}"
                                   autocomplete="off">
                            <button type="button"
                                    class="btn btn-outline-secondary sense-relation-search-btn"
                                    data-sense-index="${senseIndex}"
                                    data-relation-index="${newIndex}">
                                <i class="fas fa-search"></i> Search
                            </button>
                        </div>
                        <div class="form-text">Search by headword to change target entry/sense</div>
                        <div class="sense-relation-search-results"
                             id="sense-search-results-${senseIndex}-${newIndex}"
                             style="display: none; position: relative; z-index: 1000;">
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

  relationsContainer.insertAdjacentHTML("beforeend", newRelationHTML);

  // Initialize the new relation's dropdown with range data
  const newSelect = relationsContainer.querySelector(
    `.sense-relation-item[data-relation-index="${newIndex}"] .sense-lexical-relation-select`
  );
  if (newSelect && window.rangesLoader) {
    // Use rangesLoader to populate the select with proper range values
    window.rangesLoader
      .populateSelect(newSelect, "lexical-relation", {
        emptyOption: "Select type",
        hierarchical: true,
        searchable: true,
      })
      .catch((err) => {
        console.error(
          `[addSenseRelation] Failed to populate select via rangesLoader:`,
          err
        );
      });
  }

  // Initialize the search functionality for the new relation if the sense-relation-search handler exists
  if (window.senseRelationSearchHandler) {
    // The event listeners are already in place to handle the new elements
  }
}

/**
 * Re-indexes all sense relations for a specific sense after removal.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function reindexSenseRelations(senseIndex) {
  const relationsContainer = document.querySelector(
    `.sense-relations-container[data-sense-index="${senseIndex}"]`
  );
  if (!relationsContainer) return;

  const relationItems = relationsContainer.querySelectorAll(
    ".sense-relation-item"
  );
  relationItems.forEach((relation, newIndex) => {
    const oldIndex = relation.dataset.relationIndex;
    if (oldIndex === newIndex.toString()) return;

    // Update visual elements
    relation.querySelector(
      ".card-header span"
    ).innerHTML = `<i class="fas fa-link"></i> Relation ${newIndex + 1}`;

    // Update data attribute
    relation.dataset.relationIndex = newIndex;

    // Update all name attributes
    relation.querySelectorAll("[name]").forEach((input) => {
      const name = input.getAttribute("name");
      const newName = name.replace(
        new RegExp(
          `senses\\[${senseIndex}\\]\\.relations\\[${oldIndex}\\]`,
          "g"
        ),
        `senses[${senseIndex}].relations[${newIndex}]`
      );
      input.setAttribute("name", newName);
    });

    // Update data-relation-index and other data attributes on buttons and other elements
    relation.querySelectorAll("[data-relation-index]").forEach((btn) => {
      btn.dataset.relationIndex = newIndex;
    });

    // Update search input data attributes
    relation
      .querySelectorAll(
        ".sense-relation-search-input, .sense-relation-search-btn"
      )
      .forEach((el) => {
        el.dataset.relationIndex = newIndex;
      });

    // Update search results container ID
    const oldResultsId = `sense-search-results-${senseIndex}-${oldIndex}`;
    const newResultsId = `sense-search-results-${senseIndex}-${newIndex}`;
    const resultsContainer = document.getElementById(oldResultsId);
    if (resultsContainer) {
      resultsContainer.id = newResultsId;
    }
  });
}

/**
 * Adds a new subsense field group to a specific sense (LIFT 0.13 - Day 22).
 * @param {number|string} senseIndex - The index of the parent sense.
 */
async function addSubsense(senseIndex) {
  const subsensesContainer = document.querySelector(
    `.subsenses-container[data-sense-index="${senseIndex}"]`
  );
  const templateEl = document.getElementById("subsense-template");
  if (!subsensesContainer || !templateEl) return;

  const newIndex = subsensesContainer.querySelectorAll(".subsense-item").length;
  const newNumber = newIndex + 1;

  let template = templateEl.innerHTML
    .replace(/SENSE_INDEX/g, senseIndex)
    .replace(/SUBSENSE_INDEX/g, newIndex)
    .replace(/NUMBER/g, newNumber);

  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = template;
  const newSubsenseElement = tempDiv.firstElementChild;
  subsensesContainer.appendChild(newSubsenseElement);

  // Populate grammatical info select for the new subsense
  const grammaticalSelect = newSubsenseElement.querySelector(
    ".dynamic-grammatical-info"
  );
  if (grammaticalSelect && window.rangesLoader) {
    await window.rangesLoader.populateSelect(
      grammaticalSelect,
      "grammatical-info",
      {
        emptyOption: "Select part of speech",
      }
    );
  }
}

/**
 * Adds a nested subsense (subsense within subsense) - recursive support.
 * @param {number|string} senseIndex - The index of the parent sense.
 * @param {number|string} parentSubsenseIndex - The index of the parent subsense.
 */
async function addNestedSubsense(senseIndex, parentSubsenseIndex) {
  const nestedContainer = document.querySelector(
    `.subsense-item[data-subsense-index="${parentSubsenseIndex}"] .nested-subsenses-container`
  );
  const templateEl = document.getElementById("subsense-template");
  if (!nestedContainer || !templateEl) return;

  const newIndex = nestedContainer.querySelectorAll(".subsense-item").length;
  const newNumber = newIndex + 1;

  // For nested subsenses, use a compound index
  const nestedIndexPath = `${parentSubsenseIndex}_${newIndex}`;

  let template = templateEl.innerHTML
    .replace(/SENSE_INDEX/g, senseIndex)
    .replace(/SUBSENSE_INDEX/g, nestedIndexPath)
    .replace(/NUMBER/g, newNumber);

  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = template;
  const newSubsenseElement = tempDiv.firstElementChild;

  // Clear placeholder text if exists
  if (nestedContainer.textContent.includes("No nested subsenses yet")) {
    nestedContainer.innerHTML = "";
  }

  nestedContainer.appendChild(newSubsenseElement);

  // Populate grammatical info select
  const grammaticalSelect = newSubsenseElement.querySelector(
    ".dynamic-grammatical-info"
  );
  if (grammaticalSelect && window.rangesLoader) {
    await window.rangesLoader.populateSelect(
      grammaticalSelect,
      "grammatical-info",
      {
        emptyOption: "Select part of speech",
      }
    );
  }
}

/**
 * Re-indexes all subsenses for a specific sense.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function reindexSubsenses(senseIndex) {
  const subsensesContainer = document.querySelector(
    `.subsenses-container[data-sense-index="${senseIndex}"]`
  );
  if (!subsensesContainer) return;

  const subsenseItems = subsensesContainer.querySelectorAll(
    ":scope > .subsense-item"
  );
  subsenseItems.forEach((subsense, newIndex) => {
    const oldIndex = subsense.dataset.subsenseIndex;
    if (oldIndex === newIndex.toString()) return;

    // Update visual elements
    subsense.querySelectorAll("small").forEach((small) => {
      if (small.textContent.includes("Subsense")) {
        small.innerHTML = `<i class="fas fa-level-down-alt"></i> Subsense ${
          newIndex + 1
        }`;
      }
    });

    // Update data attribute
    subsense.dataset.subsenseIndex = newIndex;

    // Update all name attributes
    subsense.querySelectorAll("[name]").forEach((input) => {
      const name = input.getAttribute("name");
      const newName = name.replace(
        new RegExp(`senses\\[${senseIndex}\\]\\.subsenses\\[${oldIndex}\\]`),
        `senses[${senseIndex}].subsenses[${newIndex}]`
      );
      input.setAttribute("name", newName);
    });

    // Update data-subsense-index on buttons
    subsense.querySelectorAll("[data-subsense-index]").forEach((btn) => {
      btn.dataset.subsenseIndex = newIndex;
    });
  });
}

// --- LIFT 0.13: Reversal Functions (Day 24-25) ---

/**
 * Adds a new reversal to a specific sense.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
async function addReversal(senseIndex) {
  const reversalsContainer = document.querySelector(
    `.reversals-container[data-sense-index="${senseIndex}"]`
  );
  const templateEl = document.getElementById("reversal-template");
  if (!reversalsContainer || !templateEl) return;

  const newIndex = reversalsContainer.querySelectorAll(".reversal-item").length;
  const newNumber = newIndex + 1;

  let template = templateEl.innerHTML
    .replace(/SENSE_INDEX/g, senseIndex)
    .replace(/REVERSAL_INDEX/g, newIndex)
    .replace(/NUMBER/g, newNumber);

  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = template;
  const newReversalElement = tempDiv.firstElementChild;

  // Remove "no reversals" placeholder if exists
  const noReversalsPlaceholder =
    reversalsContainer.querySelector(".no-reversals");
  if (noReversalsPlaceholder) {
    noReversalsPlaceholder.remove();
  }

  reversalsContainer.appendChild(newReversalElement);

  // Populate reversal type select
  const typeSelect = newReversalElement.querySelector(".reversal-type-select");
  if (typeSelect && window.rangesLoader) {
    await window.rangesLoader.populateSelect(typeSelect, "reversal-type", {
      emptyOption: "-- Select Language --",
    });
  }

  // Populate grammatical info selects
  const grammaticalSelects = newReversalElement.querySelectorAll(
    ".dynamic-grammatical-info"
  );
  grammaticalSelects.forEach(async (select) => {
    if (window.rangesLoader) {
      await window.rangesLoader.populateSelect(select, "grammatical-info", {
        emptyOption: "-- Select --",
      });
    }
  });
}

/**
 * Removes a reversal from a specific sense.
 * @param {Element} reversalItem - The reversal item element to remove.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function removeReversal(reversalItem, senseIndex) {
  if (!reversalItem) return;

  const reversalsContainer = reversalItem.closest(".reversals-container");
  reversalItem.remove();

  // If no more reversals, show placeholder
  const remainingReversals =
    reversalsContainer.querySelectorAll(".reversal-item");
  if (remainingReversals.length === 0) {
    const placeholder = document.createElement("div");
    placeholder.className =
      "no-reversals text-center text-muted py-2 border border-info border-opacity-25 rounded";
    placeholder.innerHTML =
      '<p class="mb-2"><small>No reversals yet. Add reversals for bilingual dictionary support.</small></p>';
    reversalsContainer.appendChild(placeholder);
  } else {
    // Re-index remaining reversals
    reindexReversals(senseIndex);
  }
}

/**
 * Re-indexes all reversals for a specific sense after removal.
 * @param {number|string} senseIndex - The index of the parent sense.
 */
function reindexReversals(senseIndex) {
  const reversalsContainer = document.querySelector(
    `.reversals-container[data-sense-index="${senseIndex}"]`
  );
  if (!reversalsContainer) return;

  const reversalItems = reversalsContainer.querySelectorAll(".reversal-item");
  reversalItems.forEach((reversal, newIndex) => {
    const oldIndex = reversal.dataset.reversalIndex;
    if (oldIndex === newIndex.toString()) return;

    // Update visual elements
    reversal.querySelector(
      ".card-header span"
    ).innerHTML = `<i class="fas fa-language"></i> Reversal ${newIndex + 1}`;

    // Update data attribute
    reversal.dataset.reversalIndex = newIndex;

    // Update all name attributes
    reversal.querySelectorAll("[name]").forEach((input) => {
      const name = input.getAttribute("name");
      const newName = name.replace(
        new RegExp(`senses\\[${senseIndex}\\]\\.reversals\\[${oldIndex}\\]`),
        `senses[${senseIndex}].reversals[${newIndex}]`
      );
      input.setAttribute("name", newName);
    });

    // Update data-reversal-index on buttons
    reversal.querySelectorAll("[data-reversal-index]").forEach((btn) => {
      btn.dataset.reversalIndex = newIndex;
    });

    // Update collapse target IDs for main element
    const toggleBtn = reversal.querySelector(".toggle-main-btn");
    const collapseDiv = reversal.querySelector(".collapse");
    if (toggleBtn && collapseDiv) {
      const newId = `reversal-main-${senseIndex}-${newIndex}`;
      toggleBtn.setAttribute("data-bs-target", `#${newId}`);
      collapseDiv.id = newId;
    }
  });
}

// --- Re-indexing Functions (STAGE 1: no-ops — Alpine owns sense ordering) ---

/**
 * Re-indexes all sense fields after a sense is removed.
 * STAGE 1: No-op. Alpine manages sense ordering via reactive arrays.
 * Will be deleted in Stage 3.
 */
function reindexSenses() {
  console.debug("[reindexSenses] Stage 1: sense ordering managed by Alpine — no-op");
}

/**
 * Re-indexes example fields within a sense after one is removed.
 * STAGE 1: No-op. Alpine manages example ordering via reactive arrays.
 * Will be deleted in Stage 3.
 */
function reindexExamples(senseIndex) {
  console.debug("[reindexExamples] Stage 1: example ordering managed by Alpine — no-op");
}

/**
 * Calls the backend API to generate audio for a pronunciation.
 * @param {string} word - The lexical unit.
 * @param {string} ipa - The IPA transcription.
 * @param {number|string} index - The index of the pronunciation item.
 */
function generateAudio(word, ipa, index) {
  const btn = document.querySelector(
    `.generate-audio-btn[data-index="${index}"]`
  );
  if (!btn) return;

  // Check if we have either word or IPA to generate from
  if (!word || word.trim() === "") {
    showToast(
      "Please enter a lexical unit (word) to generate audio",
      "warning"
    );
    return;
  }

  const originalText = btn.innerHTML;
  btn.innerHTML =
    '<span class="spinner-border spinner-border-sm"></span> Generating...';
  btn.disabled = true;

  // Get CSRF token
  const headers = getCsrfHeaders({ "Content-Type": "application/json" });

  fetch("/api/pronunciations/generate", {
    method: "POST",
    headers: headers,
    body: JSON.stringify({
      word,
      ipa, // Can be empty - backend will use word text for TTS
    }),
  })
    .then(async (response) => {
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(
          errData.message ||
            `Audio generation failed with status: ${response.status}`
        );
      }
      return response.json();
    })
    .then((data) => {
      if (!data.audio_url) {
        throw new Error("API response did not include an audio URL.");
      }
      const audioPlayer = document.getElementById("audio-preview-player");
      audioPlayer.src = data.audio_url;
      audioPlayer.dataset.pronunciationIndex = index;

      const audioPreviewModal =
        bootstrap.Modal.getOrCreateInstance("#audioPreviewModal");
      audioPreviewModal.show();
    })
    .catch((error) => {
      console.error("Error generating audio:", error);
      showToast(`Error generating audio: ${error.message}`, "error");
    })
    .finally(() => {
      btn.innerHTML = originalText;
      btn.disabled = false;
    });
}

// Event listener for removing language fields from annotations
document.addEventListener("click", (e) => {
  const removeLanguageBtn = e.target.closest(".remove-annotation-language-btn");
  if (removeLanguageBtn) {
    const inputGroup = removeLanguageBtn.closest(".input-group");
    if (inputGroup && confirm("Remove this language?")) {
      inputGroup.remove();
    }
  }
});

/**
 * Add a language field to a custom field (literal-meaning, exemplar, scientific-name).
 * @param {Element} button - The "Add Language" button element.
 * @param {string} fieldType - The type of custom field ('literal-meaning', 'exemplar', 'scientific-name')
 */
function addCustomFieldLanguage(button, fieldType) {
  // Find the container for this field type
  const formsContainer = button
    .closest(".mb-3, .card-body")
    .querySelector(`.${fieldType}-forms`);

  if (!formsContainer) {
    console.error(`Could not find .${fieldType}-forms container`);
    return;
  }

  // Prompt for language code
  const langCode = prompt("Enter language code (e.g., en, fr, es):");
  if (!langCode || !langCode.trim()) return;

  const sanitizedLang = langCode.trim().toLowerCase();

  // Check if language already exists
  const existingLangSelects = formsContainer.querySelectorAll(
    "select.language-selector"
  );
  for (const select of existingLangSelects) {
    if (select.value === sanitizedLang) {
      alert(`Language "${sanitizedLang}" already exists.`);
      return;
    }
  }

  // Determine name prefix based on field type and context (entry or sense)
  let namePrefix = "";
  const senseCard = button.closest(".sense-card");

  if (senseCard) {
    // This is a sense-level field
    const senseIndex = senseCard.dataset.senseIndex;
    if (fieldType === "exemplar") {
      namePrefix = `senses[${senseIndex}].exemplar.`;
    } else if (fieldType === "scientific-name") {
      namePrefix = `senses[${senseIndex}].scientific-name.`;
    }
  } else {
    // This is an entry-level field
    if (fieldType === "literal-meaning") {
      namePrefix = `literal-meaning.`;
    }
  }

  // Get available languages for the selector
  const languagesJson = document.getElementById(
    "project-languages-data"
  )?.textContent;
  let languageOptions = [];
  if (languagesJson) {
    try {
      const languages = JSON.parse(languagesJson);
      languageOptions = languages
        .map(
          ([code, label]) =>
            `<option value="${code}" ${
              code === sanitizedLang ? "selected" : ""
            }>${label}</option>`
        )
        .join("");
    } catch (e) {
      console.error("Failed to parse project languages:", e);
    }
  }

  // Create new language form group
  const removeButtonClass = `remove-${fieldType}-language-btn`;
  const textareaClass = `${fieldType}-text`;

  const newLangHTML = `
        <div class="language-form-group mb-2">
            <div class="row">
                <div class="col-md-3">
                    <select class="form-select language-selector" 
                            name="${namePrefix}${sanitizedLang}_lang">
                        ${languageOptions}
                    </select>
                </div>
                <div class="col-md-8">
                    <textarea class="form-control ${textareaClass}" 
                           name="${namePrefix}${sanitizedLang}"
                           rows="2"
                           placeholder="Enter ${fieldType} in ${sanitizedLang}"></textarea>
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-outline-danger ${removeButtonClass}" 
                            title="Remove this language">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        </div>
    `;

  formsContainer.insertAdjacentHTML("beforeend", newLangHTML);
}

// Event listeners for removing custom field language forms
document.addEventListener("click", (e) => {
  // Literal meaning remove button
  const removeLiteralMeaningBtn = e.target.closest(
    ".remove-literal-meaning-language-btn"
  );
  if (removeLiteralMeaningBtn) {
    const formGroup = removeLiteralMeaningBtn.closest(".language-form-group");
    if (formGroup && confirm("Remove this language?")) {
      formGroup.remove();
    }
    return;
  }

  // Exemplar remove button
  const removeExemplarBtn = e.target.closest(".remove-exemplar-language-btn");
  if (removeExemplarBtn) {
    const formGroup = removeExemplarBtn.closest(".language-form-group");
    if (formGroup && confirm("Remove this language?")) {
      formGroup.remove();
    }
    return;
  }

  // Scientific name remove button
  const removeScientificNameBtn = e.target.closest(
    ".remove-scientific-name-language-btn"
  );
  if (removeScientificNameBtn) {
    const formGroup = removeScientificNameBtn.closest(".language-form-group");
    if (formGroup && confirm("Remove this language?")) {
      formGroup.remove();
    }
    return;
  }
});

//
