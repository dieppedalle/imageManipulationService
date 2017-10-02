import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.sqlite import BLOB

# Create an instance of our web app.
app = Flask(__name__)

# Define the database containing our tables.
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///imageManipulation.db"

db = SQLAlchemy()
db.init_app(app)


# SQLAlchemy object for user uploads
class Uploads(db.Model):
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