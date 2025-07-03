"""
Create a minimal test script to show how the value is being set in the input field.
"""

def create_minimal_test():
    """Create a minimal test HTML file to show how the input value is set."""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Input Value Test</title>
</head>
<body>
    <h1>Input Value Test</h1>
    
    <div id="test-container"></div>
    
    <script>
        // Test values
        const normalValue = "ˈprɒtɪstəntɪzm";
        const emptyValue = "";
        const nullValue = null;
        const undefinedValue = undefined;
        
        // Create a function to render inputs with different values
        function renderInput(containerId, label, value) {
            const container = document.getElementById(containerId);
            const html = `
                <div class="test-item">
                    <h3>${label}</h3>
                    <p>JavaScript value: "${value}" (${typeof value})</p>
                    <input type="text" name="test-${label}" value="${value || ''}" />
                    <p>With || '': <code>value="${value || ''}"</code></p>
                    
                    <input type="text" name="test-${label}-2" value="${value ? value : ''}" />
                    <p>With ternary: <code>value="${value ? value : ''}"</code></p>
                </div>
                <hr>
            `;
            container.insertAdjacentHTML('beforeend', html);
        }
        
        // Render test inputs
        renderInput('test-container', 'Normal', normalValue);
        renderInput('test-container', 'Empty', emptyValue);
        renderInput('test-container', 'Null', nullValue);
        renderInput('test-container', 'Undefined', undefinedValue);
    </script>
</body>
</html>
"""
    
    # Write to a file
    with open('input_value_test.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("Test page created: input_value_test.html")
    print("Open this file in a web browser to test how values are set in input fields.")

if __name__ == '__main__':
    create_minimal_test()
