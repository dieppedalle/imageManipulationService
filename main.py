import cStringIO
import cv2
import io
import json
import numpy as np
import PIL.Image
import sys
from base64 import b64encode
from datetime import datetime
from flask import Flask, jsonify, render_template, request
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


def updateDatabase(id, imageBinary):
    """
    Adds a record to the database.
    """
    fileDatabase = db.session.query(Uploads) \
                     .filter(Uploads.id == id)\
                     .first()
    if not fileDatabase:
        return jsonify(success=0)
    
    height, width, _ = getSizeImage(imageBinary)
    
    fileDatabase.imageBinary = imageBinary
    fileDatabase.height = height
    fileDatabase.width = width
    fileDatabase.numTimesUpdated += 1
    db.session.commit()
    
    return jsonify(success=1)


def isInt(s):
    """
    Checks if the given string can be translated to an integer.
    """
    try: 
        int(s)
        return True
    except ValueError:
        return False


@app.route("/v1/image")
def getMetadata():
    """
    Route used if the user wants to logout.
    """
    fileDatabase = db.session.query(Uploads)
    
    result = []
    
    # Iterate through the files in the database.
    for file in fileDatabase:
        data = {}
        data['id'] = file.id
        data['filename'] = file.filename
        data['creationDate'] = str(file.creationDate)
        data['fileSize'] = file.fileSize
        data['fileType'] = file.fileType
        data['height'] = file.height
        data['width'] = file.width
        data['numTimesUpdated'] = file.numTimesUpdated
        result.append(data)
    return json.dumps(result)


@app.route("/v1/image/<id>")
def getMetadataForId(id):
    """
    Route used if the user wants to logout.
    """
    fileDatabase = db.session.query(Uploads) \
                     .filter(Uploads.id == id)\
                     .first()
    
    if not fileDatabase:
        return jsonify(success=0)
    
    data = {}
    data['id'] = fileDatabase.id
    data['filename'] = fileDatabase.filename
    data['creationDate'] = str(fileDatabase.creationDate)
    data['fileSize'] = fileDatabase.fileSize
    data['fileType'] = fileDatabase.fileType
    data['height'] = fileDatabase.height
    data['width'] = fileDatabase.width
    data['numTimesUpdated'] = fileDatabase.numTimesUpdated
    
    return json.dumps(data)


@app.route("/v1/image/<id>/data")
def getImageForId(id):
    """
    Route used if the user wants to logout.
    """
    if not isInt(id):
        return jsonify(success=0)
        
    fileDatabase = db.session.query(Uploads).filter(Uploads.id == id).first()
    
    if not fileDatabase:
        return jsonify(success=0)
    
    arguments = request.args.get('bbox')
    if arguments:
        argumentsList = arguments.split(',')
        
        for arg in argumentsList:
            if not isInt(arg):
                return jsonify(success=0)
            
        argumentsList = map(int, argumentsList)
        
        fileStringIO = cStringIO.StringIO(fileDatabase.imageBinary)

        pilImg = PIL.Image.open(fileStringIO)
        pilImgCropped = pilImg.crop(argumentsList)
        
        imgByteArr = io.BytesIO()
        pilImgCropped.save(imgByteArr, format='PNG')
        imgByteArr = imgByteArr.getvalue()
        
        return render_template('showImage.html', image=b64encode(imgByteArr))
    
    return render_template('showImage.html', image=b64encode(fileDatabase.imageBinary))


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


@app.route("/v1/image/<id>", methods=['PUT'])
def updateImage(id):
    """
    Root that redirects the user to the homepage.
    """
    if not request.data:
        return jsonify(success=0)
    
    updateDatabase(id, request.data)
            
    return jsonify(success=1)


@app.errorhandler(404)
def page_not_found(error):
    """
    Handles 404 errors. If page is not found.
    """
    app.logger.error('Page not found: %s', (request.path))
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(error):
    """
    Handles 500 errors. If error happened.
    """
    app.logger.error('Server Error: %s', (error))
    return render_template('500.html'), 500


@app.errorhandler(Exception)
def unhandled_exception(error):
    """
    Handles all other errors.
    """
    app.logger.error('Unhandled Exception: %s', (error))
    return render_template('unhandledError.html')

    
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