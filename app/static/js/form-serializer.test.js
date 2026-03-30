/**
 * Unit Tests for Form Serializer
 * 
 * Comprehensive test suite for the form serialization utility.
 * Can be run in Node.js environment or browser console.
 */

// Test framework - simple assertion library
function assert(condition, message) {
    if (!condition) {
        throw new Error(`Assertion failed: ${message}`);
    }
}

function assertEqual(actual, expected, message) {
    // Convert both to JSON strings for comparison, which handles undefined -> null conversion
    const actualJson = JSON.stringify(actual);
    const expectedJson = JSON.stringify(expected);
    if (actualJson !== expectedJson) {
        throw new Error(`Assertion failed: ${message}\nExpected: ${expectedJson}\nActual: ${actualJson}`);
    }
}

function assertThrows(fn, expectedError, message) {
    try {
        fn();
        throw new Error(`Expected function to throw, but it didn't: ${message}`);
    } catch (error) {
        if (expectedError && !error.message.includes(expectedError)) {
            throw new Error(`Expected error containing "${expectedError}", got: ${error.message}`);
        }
    }
}

// Load the module (adjust path as needed)
let FormSerializer;
if (typeof require !== 'undefined') {
    // Node.js environment
    FormSerializer = require('./form-serializer.js');
} else {
    // Browser environment - assume it's already loaded
    FormSerializer = window.FormSerializer;
}

const { serializeFormToJSON, setNestedValue, parseFieldPath, validateFormForSerialization } = FormSerializer;

/**
 * Test Suite: parseFieldPath function
 */
function testParseFieldPath() {
    console.log('Testing parseFieldPath...');
    
    // Test simple field
    let result = parseFieldPath('name');
    assertEqual(result, [{ key: 'name', isArrayIndex: false }], 'Simple field parsing');
    
    // Test dot notation
    result = parseFieldPath('user.name');
    assertEqual(result, [
        { key: 'user', isArrayIndex: false },
        { key: 'name', isArrayIndex: false }
    ], 'Dot notation parsing');
    
    // Test complex dot notation
    result = parseFieldPath('user.address.city');
    assertEqual(result, [
        { key: 'user', isArrayIndex: false },
        { key: 'address', isArrayIndex: false },
        { key: 'city', isArrayIndex: false }
    ], 'Complex dot notation parsing');
    
    // Test simple array notation
    result = parseFieldPath('items[0]');
    assertEqual(result, [
        { key: 'items', isArrayIndex: false },
        { key: '0', isArrayIndex: true }
    ], 'Simple array notation parsing');
    
    // Test complex array notation
    result = parseFieldPath('senses[0].definition');
    assertEqual(result, [
        { key: 'senses', isArrayIndex: false },
        { key: '0', isArrayIndex: true },
        { key: 'definition', isArrayIndex: false }
    ], 'Complex array notation parsing');
    
    // Test multiple dots after array
    result = parseFieldPath('senses[0].grammatical_info.part_of_speech');
    assertEqual(result, [
        { key: 'senses', isArrayIndex: false },
        { key: '0', isArrayIndex: true },
        { key: 'grammatical_info', isArrayIndex: false },
        { key: 'part_of_speech', isArrayIndex: false }
    ], 'Multiple dots after array parsing');
    
    // Test multiple arrays
    result = parseFieldPath('senses[0].examples[0].text');
    assertEqual(result, [
        { key: 'senses', isArrayIndex: false },
        { key: '0', isArrayIndex: true },
        { key: 'examples', isArrayIndex: false },
        { key: '0', isArrayIndex: true },
        { key: 'text', isArrayIndex: false }
    ], 'Multiple array levels parsing');
    
    console.log('✓ parseFieldPath tests passed');
}

/**
 * Test Suite: setNestedValue function
 */
function testSetNestedValue() {
    console.log('Testing setNestedValue...');
    
    // Test simple value
    let obj = {};
    setNestedValue(obj, 'name', 'John');
    assertEqual(obj, { name: 'John' }, 'Simple value setting');
    
    // Test dot notation
    obj = {};
    setNestedValue(obj, 'user.name', 'John');
    assertEqual(obj, { user: { name: 'John' } }, 'Dot notation value setting');
    
    // Test array notation
    obj = {};
    setNestedValue(obj, 'items[0]', 'first');
    assertEqual(obj, { items: ['first'] }, 'Array notation value setting');
    
    // Test complex notation
    obj = {};
    setNestedValue(obj, 'senses[0].definition', 'A word meaning');
    assertEqual(obj, { senses: [{ definition: 'A word meaning' }] }, 'Complex notation value setting');
    
    // Test multiple values in same array
    obj = {};
    setNestedValue(obj, 'senses[0].definition', 'First definition');
    setNestedValue(obj, 'senses[0].id', 'sense-1');
    setNestedValue(obj, 'senses[1].definition', 'Second definition');
    assertEqual(obj, {
        senses: [
            { definition: 'First definition', id: 'sense-1' },
            { definition: 'Second definition' }
        ]
    }, 'Multiple array values setting');
    
    console.log('✓ setNestedValue tests passed');
}

/**
 * Test Suite: serializeFormToJSON function
 */
function testSerializeFormToJSON() {
    console.log('Testing serializeFormToJSON...');
    
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

    function createMockFormDataWithElements(entries, elementSpecsByName) {
        return {
            entries: entries,
            forEach: function(callback) {
                this.entries.forEach(([key, value]) => callback(value, key));
            },
            querySelectorAll: function(selector) {
                const match = /^\[name="(.+)"\]$/.exec(selector);
                if (!match) return [];

                // Undo minimal escaping used by the serializer.
                const name = match[1].replace(/\\(.)/g, '$1');
                return (elementSpecsByName[name] || []).map(spec => ({
                    tagName: spec.tagName,
                    type: spec.type,
                    multiple: !!spec.multiple
                }));
            }
        };
    }
    
    // Test simple form data
    let formData = createMockFormData([
        ['name', 'John Doe'],
        ['email', 'john@example.com']
    ]);
    
    let result = serializeFormToJSON(formData);
    assertEqual(result, {
        name: 'John Doe',
        email: 'john@example.com'
    }, 'Simple form data serialization');
    
    // Test complex form data
    formData = createMockFormData([
        ['lexical_unit', 'test word'],
        ['senses[0].id', 'sense-1'],
        ['senses[0].definition', 'First meaning'],
        ['senses[1].id', 'sense-2'],
        ['senses[1].definition', 'Second meaning'],
        ['grammatical_info.part_of_speech', 'noun']
    ]);
    
    result = serializeFormToJSON(formData);
    assertEqual(result, {
        lexical_unit: 'test word',
        senses: [
            { id: 'sense-1', definition: 'First meaning' },
            { id: 'sense-2', definition: 'Second meaning' }
        ],
        grammatical_info: { part_of_speech: 'noun' }
    }, 'Complex form data serialization');
    
    // Test empty values option

    // Worker-like behavior: duplicate non-multi fields must not become arrays
    formData = createMockFormData([
        ['senses[1].id', ''],
        ['senses[1].id', 'sense-2'],
        ['senses[1].definition.en.text', 'Old'],
        ['senses[1].definition.en.text', 'New']
    ]);
    result = serializeFormToJSON(formData);
    assertEqual(result, {
        senses: [
            ,
            { id: 'sense-2', definition: { en: { text: 'New' } } }
        ]
    }, 'Duplicate scalar fields are coerced (worker-like input)');

    // Worker-like behavior: known multi-select fields preserve arrays
    formData = createMockFormData([
        ['senses[0].semantic_domain', '1.1'],
        ['senses[0].semantic_domain', '1.2'],
        ['senses[0].usage_type', 'formal'],
        ['senses[0].usage_type', 'archaic'],
        ['senses[0].domain_type', 'biology'],
        ['senses[0].domain_type', 'chemistry']
    ]);
    result = serializeFormToJSON(formData);
    assertEqual(result, {
        senses: [
            {
                semantic_domain: ['1.1', '1.2'],
                usage_type: ['formal', 'archaic'],
                domain_type: ['biology', 'chemistry']
            }
        ]
    }, 'Known multi-select fields preserve arrays (worker-like input)');
    formData = createMockFormData([
        ['name', 'John'],
        ['description', ''],
        ['email', 'john@example.com']
    ]);
    
    result = serializeFormToJSON(formData, { includeEmpty: false });
    assertEqual(result, {
        name: 'John',
        email: 'john@example.com'
    }, 'Exclude empty values option');
    
    // Test transform function
    formData = createMockFormData([
        ['name', 'john doe'],
        ['age', '25']
    ]);
    
    result = serializeFormToJSON(formData, {
        transform: (value, key) => {
            if (key === 'name') return value.toUpperCase();
            if (key === 'age') return parseInt(value);
            return value;
        }
    });
    assertEqual(result, {
        name: 'JOHN DOE',
        age: 25
    }, 'Transform function option');

    // Test duplicate field names (non-multiple controls) are coerced to scalar
    formData = createMockFormDataWithElements(
        [
            ['senses[1].id', ''],
            ['senses[1].id', 'sense-2']
        ],
        {
            'senses[1].id': [
                { tagName: 'input', type: 'hidden' },
                { tagName: 'input', type: 'hidden' }
            ]
        }
    );
    result = serializeFormToJSON(formData);
    assertEqual(result, { senses: [null, { id: 'sense-2' }] }, 'Duplicate hidden inputs coerce to scalar');

    // Test legitimate multi-select preserves array
    formData = createMockFormDataWithElements(
        [
            ['senses[0].semantic_domain', '1.2'],
            ['senses[0].semantic_domain', '1.3']
        ],
        {
            'senses[0].semantic_domain': [
                { tagName: 'select', multiple: true }
            ]
        }
    );
    result = serializeFormToJSON(formData);
    assertEqual(result, { senses: [{ semantic_domain: ['1.2', '1.3'] }] }, 'Multi-select keeps array');
    
    console.log('✓ serializeFormToJSON tests passed');
}

/**
 * Test Suite: Edge cases and error handling
 */
function testEdgeCases() {
    console.log('Testing edge cases...');
    
    // Test invalid input
    assertThrows(() => {
        serializeFormToJSON("invalid input");
    }, 'Input must be an HTMLFormElement, FormData object, or FormData-like object', 'Invalid input handling');
    
    // Test empty form data
    let formData = {
        entries: [],
        forEach: function(callback) {
            this.entries.forEach(([key, value]) => callback(value, key));
        }
    };
    
    let result = serializeFormToJSON(formData);
    assertEqual(result, {}, 'Empty form data handling');
    
    // Test gaps in array indices
    formData = {
        entries: [
            ['items[0]', 'first'],
            ['items[2]', 'third'] // Missing index 1
        ],
        forEach: function(callback) {
            this.entries.forEach(([key, value]) => callback(value, key));
        }
    };
    
    result = serializeFormToJSON(formData);
    assertEqual(result, {
        items: ['first', null, 'third']
    }, 'Gap in array indices handling');
    
    console.log('✓ Edge cases tests passed');
}

/**
 * Test Suite: Real-world scenarios
 */
function testRealWorldScenarios() {
    console.log('Testing real-world scenarios...');
    
    // Test dictionary entry form data
    let formData = {
        entries: [
            ['lexical_unit', 'protestantism'],
            ['grammatical_info.part_of_speech', 'noun'],
            ['senses[0].id', 'sense-1'],
            ['senses[0].definition', 'A form of Christianity'],
            ['senses[0].grammatical_info.part_of_speech', 'noun'],
            ['senses[0].examples[0].text', 'Protestantism emerged in the 16th century'],
            ['senses[1].id', 'sense-2'],
            ['senses[1].definition', 'Opposition to Catholicism'],
            ['pronunciations[0].value', '/ˈprɒtɪstəntɪzəm/'],
            ['pronunciations[0].type', 'IPA']
        ],
        forEach: function(callback) {
            this.entries.forEach(([key, value]) => callback(value, key));
        }
    };
    
    let result = serializeFormToJSON(formData);
    let expected = {
        lexical_unit: 'protestantism',
        grammatical_info: { part_of_speech: 'noun' },
        senses: [
            {
                id: 'sense-1',
                definition: 'A form of Christianity',
                grammatical_info: { part_of_speech: 'noun' },
                examples: [{ text: 'Protestantism emerged in the 16th century' }]
            },
            {
                id: 'sense-2',
                definition: 'Opposition to Catholicism'
            }
        ],
        pronunciations: [
            { value: '/ˈprɒtɪstəntɪzəm/', type: 'IPA' }
        ]
    };
    
    assertEqual(result, expected, 'Dictionary entry form serialization');
    
    console.log('✓ Real-world scenarios tests passed');
}

/**
 * Performance test
 */
function testPerformance() {
    console.log('Testing performance...');
    
    // Create a large form data set
    let entries = [];
    for (let i = 0; i < 1000; i++) {
        entries.push([`items[${i}].name`, `Item ${i}`]);
        entries.push([`items[${i}].value`, `Value ${i}`]);
    }
    
    let formData = {
        entries: entries,
        forEach: function(callback) {
            this.entries.forEach(([key, value]) => callback(value, key));
        }
    };
    
    let startTime = performance.now();
    let result = serializeFormToJSON(formData);
    let endTime = performance.now();
    
    console.log(`Performance test: serialized ${entries.length} fields in ${endTime - startTime} ms`);
    
    // Verify the result structure
    assert(result.items && result.items.length === 1000, 'Performance test result structure');
    assert(result.items[999].name === 'Item 999', 'Performance test result content');
    
    console.log('✓ Performance test passed');
}

/**
 * Run all tests
 */
function runAllTests() {
    console.log('🧪 Starting Form Serializer Test Suite...\n');
    
    try {
        testParseFieldPath();
        testSetNestedValue();
        testSerializeFormToJSON();
        testEdgeCases();
        testRealWorldScenarios();
        testPerformance();
        
        console.log('\n✅ All tests passed! Form Serializer is working correctly.');
        return true;
    } catch (error) {
        console.error('\n❌ Test failed:', error.message);
        console.error(error.stack);
        return false;
    }
}

// Export for both Node.js and browser environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { runAllTests };
} else if (typeof window !== 'undefined') {
    window.FormSerializerTests = { runAllTests };
}

// Auto-run tests if this file is executed directly
if (typeof require !== 'undefined' && require.main === module) {
    runAllTests();
}
