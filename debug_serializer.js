// Debug test for form serializer
const FormSerializer = require('./app/static/js/form-serializer.js');
const { serializeFormToJSON } = FormSerializer;

// Create a mock FormData object
function createMockFormData(entries) {
    const formData = {
        entries: entries,
        forEach: function(callback) {
            this.entries.forEach(([key, value]) => callback(value, key));
        }
    };
    return formData;
}

let formData = createMockFormData([
    ['items[0]', 'first'],
    ['items[2]', 'third'] // Missing index 1
]);

let result = serializeFormToJSON(formData);
console.log('Result:', JSON.stringify(result, null, 2));
console.log('items[1] type:', typeof result.items[1]);
console.log('items[1] value:', result.items[1]);

// Let's check what actually gets stored in the array
console.log('Array length:', result.items.length);
console.log('items[0]:', result.items[0]);
console.log('items[1]:', result.items[1]);
console.log('items[2]:', result.items[2]);
console.log('Has property [1]:', result.items.hasOwnProperty(1));
console.log('Array entries:', [...result.items.entries()]);

// Test different order
let formData2 = createMockFormData([
    ['items[2]', 'third'], // Process out-of-order first  
    ['items[0]', 'first']
]);

let result2 = serializeFormToJSON(formData2);
console.log('Out-of-order Result:', JSON.stringify(result2, null, 2));
