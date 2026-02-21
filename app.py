"""
Entry point for the BlackRock Challenge Flask application.

Run with:
    python app.py

Or with a production WSGI server:
    gunicorn -w 4 app:application
"""

from app import create_app

application = create_app()

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000, debug=False)
