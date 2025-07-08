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
        self.postMessage({ error: error.message });
    }
});