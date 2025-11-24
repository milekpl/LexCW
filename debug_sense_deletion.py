"""
Debug script to check what data is sent when deleting a sense.
Run the Flask app and then manually:
1. Go to http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit
2. Open browser DevTools > Network tab
3. Delete the empty sense 
4. Click Save
5. Check the request payload in the PUT request to /api/entries/...
"""

print("""
To debug sense deletion:

1. Start Flask app: python run.py
2. Open: http://localhost:5000/entries/AIDS%20test_a774b9c4-c013-4f54-9017-cf818791080c/edit
3. Open DevTools (F12) > Network tab
4. Delete the problematic sense (click the X button)
5. Check the "Skip validation" checkbox
6. Click Save
7. In Network tab, find the PUT request to /api/entries/AIDS%20test...
8. Click it and view the Request Payload
9. Count how many senses are in the payload

Expected: 1 sense (the valid one)
If you see: 2 senses (both senses still there) = BUG in form serialization

Also check the Flask console for the log message:
"Received update for entry ... with N senses"
""")
