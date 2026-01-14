/**
 * Browser test for Form Serializer
 * This file can be run in the browser console to test the form serializer
 */

// Test the form serializer in browser environment
function testFormSerializerInBrowser() {
    console.log('Testing Form Serializer in browser environment...');
    
    if (typeof window.FormSerializer === 'undefined') {
        console.error('❌ FormSerializer not loaded!');
        return false;
    }
    
    console.log('✓ FormSerializer loaded successfully');
    
    // Test basic functionality
    try {
        // Create a simple mock form data
        const mockFormData = {
            entries: [
                ['name', 'test'],
                ['senses[0].definition', 'test definition'],
                ['senses[0].examples[0].text', 'test example']
            ],
            forEach: function(callback) {
                this.entries.forEach(([key, value]) => callback(value, key));
            }
        };
        
        const result = window.FormSerializer.serializeFormToJSON(mockFormData);
        
        console.log('Test result:', result);
        
        // Verify structure
        if (result.name === 'test' && 
            result.senses && 
            result.senses[0] && 
            result.senses[0].definition === 'test definition' &&
            result.senses[0].examples &&
            result.senses[0].examples[0] &&
            result.senses[0].examples[0].text === 'test example') {
            console.log('✅ Browser test passed!');
            return true;
        } else {
            console.error('❌ Browser test failed - unexpected result structure');
            return false;
        }
        
    } catch (error) {
        console.error('❌ Browser test failed with error:', error);
        return false;
    }
}

// Export to window for manual testing
window.testFormSerializerInBrowser = testFormSerializerInBrowser;

console.log('Browser test loaded. Run testFormSerializerInBrowser() to test.');
