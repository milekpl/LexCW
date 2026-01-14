/**
 * Form Serializer Worker
 * 
 * A Web Worker implementation of the form serializer to prevent UI freezing
 * when processing large forms.
 */

// Import the serialization functions
self.importScripts('/static/js/form-serializer.js');

// Listen for messages from the main thread
self.addEventListener('message', function(e) {
    try {
        const { formData, options } = e.data;
        // Diagnostic logging: report how many entries and a small sample
        try {
            const count = Array.isArray(formData) ? formData.length : (formData && formData.length) || 0;
            const sampleNames = (Array.isArray(formData) ? formData.slice(0,10) : formData).map ? (Array.isArray(formData) ? formData.slice(0,10).map(e => e[0]) : []) : [];
            // use postMessage back to main thread to avoid console in worker environments
            self.postMessage({ __debug: { receivedCount: count, sampleNames } });
        } catch (dbgErr) {
            // ignore logging errors
        }
        
        // Create a FormData-like object from the array
        const formDataObj = {
            entries: formData,
            forEach: function(callback) {
                this.entries.forEach(entry => callback(entry[1], entry[0]));
            }
        };
        
        // Serialize the form data
        const result = serializeFormToJSON(formDataObj, options);
        
        // Send the result back to the main thread
        self.postMessage({ result });
    } catch (error) {
        // Send any errors back to the main thread
        const payload = { error: error.message };
        if (error.stack) payload.stack = error.stack;
        self.postMessage(payload);
    }
});