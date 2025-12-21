import tkinter as tk
from src.gui import App

if __name__ == '__main__':
    # For Docker, bind to 0.0.0.0
    app.run(host='0.0.0.0', port=5000, debug=False)
