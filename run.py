import os
from app import create_app

app = create_app()

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

if __name__ == "__main__":
    app.run(debug=True)

