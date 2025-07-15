import os
import sys
from app import create_app

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

app = create_app()

if __name__ == '__main__':
    # Ensure paths exist
    os.makedirs(resource_path('app/data'), exist_ok=True)
    app.run(host='0.0.0.0', port=5000)