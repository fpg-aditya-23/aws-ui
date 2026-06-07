# Deployment Guide

This app is a Flask web application and can be published to a free Python host.

## Option 1: PythonAnywhere (easy, free tier)

1. Create a free account at https://www.pythonanywhere.com/
2. Upload this project using the Files page, or connect a GitHub repo.
3. In the PythonAnywhere Dashboard, create a new web app:
   - Choose `Flask`
   - Choose Python 3.11 or 3.10
   - Set the source code directory to the project folder.
4. Edit the WSGI configuration file to point to `app.py`:
   - Replace the default WSGI app import with:
     ```python
     import sys
     path = '/home/yourusername/path/to/project'
     if path not in sys.path:
         sys.path.insert(0, path)
     from app import app as application
     ```
5. Install dependencies in the Bash console:
   ```bash
   pip install -r requirements.txt
   ```
6. Reload the web app.

## Option 2: Render (free web services)

1. Create a free account at https://render.com/
2. Push this project to GitHub.
3. Create a new Web Service from your GitHub repository.
4. Use `Python 3` and set the build command to:
   ```bash
   pip install -r requirements.txt
   ```
5. Set the start command to:
   ```bash
   gunicorn app:app
   ```
6. Deploy and open the service URL.

## Option 3: Railway / Fly.io / Replit

Any free Python host that supports Flask and `requirements.txt` can run this app.

## Notes

- The app currently uses local file paths from the server. Ensure the server has access to the same directories or update the paths accordingly.
- If the host does not allow direct file-system access, use a server-side mount or adjust the download logic.
