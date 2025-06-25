from flask import Flask
import os

# Set the correct environment variable for the database
os.environ['BASEX_DATABASE'] = 'dictionary'

# Import the create_app function after setting the environment variable
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
