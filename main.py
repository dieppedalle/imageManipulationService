import cStringIO
import cv2
import io
import json
import numpy as np
import PIL.Image
import struct
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

db = SQLAlchemy()
db.init_app(app)

class Uploads(db.Model):
    """
    SQLAlchemy object for image uploads.
    """
    __tablename__ = 'Images'
    id = db.Column(db.Integer, primary_key=True)
    imageBinary = db.Column(BLOB)
    creationDate = db.Column(db.DateTime)
    fileSize = db.Column(db.Integer)
    fileType = db.Column(db.String(256))
    height = db.Column(db.Integer)
    width = db.Column(db.Integer)
    lastUpdateDate = db.Column(db.DateTime)

    def __init__(self, imageBinary, creationDate, height, width, imageType):
        self.imageBinary = imageBinary
        self.creationDate = creationDate
        self.fileSize = len(imageBinary)
        self.fileType = imageType
        self.height = height
        self.width = width
        self.lastUpdateDate = creationDate
        


def getImageType(data):
    """
    Returns the image type of the given binary data.
    Returns empty string if binary data is not an image.
    """
    if isGif(data):
        return "GIF"
    elif isPng(data) or isOldPng(data):
        return "PNG"
    elif isJpeg(data):
        return "JPG"
    else:
        return ""

def isGif(data):
    """
    Checks if image is a GIF. 
    Takes as input binary data of the image.
    Returns True if it is, False otherwise.
    """
    return (data[:6] in ('GIF87a', 'GIF89a'))

def isPng(data):
    """
    Checks if image is a PNG. 
    Takes as input binary data of the image.
    Returns True if it is, False otherwise.
    """
    return ((data[:8] == '\211PNG\r\n\032\n') and (data[12:16] == 'IHDR'))

def isOldPng(data):
    """
    Checks if image is a PNG (old format). 
    Takes as input binary data of the image.
    Returns True if it is, False otherwise.
    """
    return ((data[:8] == '\211PNG\r\n\032\n') and (data[12:16] != 'IHDR'))

def isJpeg(data):
    """
    Checks if image is a JPEG. 
    Takes as input binary data of the image.
    Returns True if it is, False otherwise.
    """
    return (data[:2] == '\377\330')

def isInt(s):
    """
    Checks if the given string can be translated to an integer.
    """
    try: 
        int(s)
        return True
    except ValueError:
        return False

def getSizeImage(data):
    """
    Returns the dimensions of the image with binary data.
    """
    # imdecode does not work on gif files so need to calculate the size of
    # the image manually.
    if isGif(data):
        w, h = struct.unpack('<HH', data[6:10])
        width = int(w)
        height = int(h)
        return [width, height]
    
    # Function that can be used to compute size of an image.
    nparr = np.fromstring(data, np.uint8)
    size = cv2.imdecode(nparr, cv2.IMREAD_COLOR).shape
    return [size[0], size[1]]

def addToDatabase(imageBinary, creationDate, height, width, imageType):
    """
    Adds a record to the database.
    """
    upload = Uploads(imageBinary=imageBinary, 
                     creationDate = creationDate, height = height, 
                     width = width, imageType = imageType)
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
    
    width, height = getSizeImage(imageBinary)
    
    # Update the entries of the row.
    fileDatabase.imageBinary = imageBinary
    fileDatabase.height = height
    fileDatabase.width = width
    fileDatabase.fileSize = len(imageBinary)
    fileDatabase.fileType = getImageType(imageBinary)
    fileDatabase.lastUpdateDate = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify(success=1)

def createDictMetadata(file):
    """
    Creates dictionary of data based on a file object from database.
    """
    data = {}
    data['id'] = file.id
    data['creationDate'] = str(file.creationDate)
    data['fileSize'] = file.fileSize
    data['fileType'] = file.fileType
    data['height'] = file.height
    data['width'] = file.width
    data['lastUpdateDate'] = str(file.lastUpdateDate)
    
    return data

@app.route("/v1/image")
def getMetadata():
    """
    Route used if the user wants to logout.
    """
    fileDatabase = db.session.query(Uploads)
    
    result = []
    
    # Iterate through the files in the database.
    for file in fileDatabase:
        result.append(createDictMetadata(file))
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
    
    return json.dumps(createDictMetadata(fileDatabase))

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
    
    # Checks if we need to crop the image.
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
    
    return render_template('showImage.html', 
                           image=b64encode(fileDatabase.imageBinary))

@app.route("/v1/image", methods=['POST'])
def addImage():
    """
    Root that redirects the user to the homepage.
    """
    if 'file' not in request.files:
        return jsonify(success=0)
    
    file = request.files['file']
    
    # Checks if no file have been given.
    if not file:
        return jsonify(success=0)
    
    idata = file.read()
    
    fileType = getImageType(idata)
    
    # Checks if file is not an image.
    if len(fileType) == 0:
        return jsonify(success=0)
    
    width, height = getSizeImage(idata)
    
    addToDatabase(idata, datetime.utcnow(), height, width, fileType)
    return jsonify(success=1)

@app.route("/v1/image/<id>", methods=['PUT'])
def updateImage(id):
    """
    Root that redirects the user to the homepage.
    """
    if not request.data:
        return jsonify(success=0)
    
    # Checks if file is not an image.
    if len(getImageType(request.data)) == 0:
        return jsonify(success=0)
        
    return updateDatabase(id, request.data)

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
