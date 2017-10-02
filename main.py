import cv2
import json
import numpy as np
import sys
from datetime import datetime
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import BLOB
from werkzeug.utils import secure_filename

# Create an instance of our web app.
app = Flask(__name__)

# Define the database containing our tables.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///imageManipulation.db"
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

db = SQLAlchemy()
db.init_app(app)


class Uploads(db.Model):
    """
    SQLAlchemy object for image uploads.
    """
    __tablename__ = 'Images'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256))
    imageBinary = db.Column(BLOB)
    creationDate = db.Column(db.DateTime)
    fileSize = db.Column(db.Integer)
    fileType = db.Column(db.String(256))
    height = db.Column(db.Integer)
    width = db.Column(db.Integer)
    numTimesUpdated = db.Column(db.Integer)

    def __init__(self, imageBinary, filename, creationDate, height, width):
        self.imageBinary = imageBinary
        self.filename = filename
        self.creationDate = creationDate
        self.fileSize = len(imageBinary)
        self.fileType = filename.rsplit('.', 1)[1].lower()
        self.height = height
        self.width = width
        self.numTimesUpdated = 0


def getSizeImage(idata):
    """
    Returns the dimensions of the image with binary idata.
    """
    nparr = np.fromstring(idata, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR).shape


def allowed_file(filename):
    """
    Checks whether or not the file is valid.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def addToDatabase(imageBinary, filename, creationDate, height, width):
    """
    Adds a record to the database.
    """
    upload = Uploads(imageBinary=imageBinary, filename = filename, 
                     creationDate = creationDate, height = height, 
                     width = width)
    db.session.add(upload)
    db.session.commit()


@app.route("/v1/image", methods=['POST'])
def addImage():
    """
    Root that redirects the user to the homepage.
    """
    if 'file' not in request.files:
        return jsonify(success=0)
    
    file = request.files['file']
    
    if not file:
        return jsonify(success=0)
    elif allowed_file(file.filename):
        filename = secure_filename(file.filename)
        idata = file.read()
        height, width, _ = getSizeImage(idata)
        
        addToDatabase(idata, filename, datetime.utcnow(), height, width)
    return jsonify(success=1)

    
if __name__ == "__main__":
    if "--setup" in sys.argv:
        """
        Flag used to create the initial database containing the data. 
        The setup flag should only be used once to setup the server.
        """
        with app.app_context():
            db.create_all()
            db.session.commit()
            print("Database tables created.")
    else:
        app.run(debug=True)