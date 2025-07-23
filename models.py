from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Initialize SQLAlchemy
db = SQLAlchemy()

# User Model
class User(db.Model, UserMixin):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=True)  # Changed to nullable=True to support Cognito users

    files = db.relationship('File', backref='owner', lazy=True)
    shared = db.relationship('SharedFile', backref='recipient', lazy=True)

# File Model
class File(db.Model):
    __tablename__ = 'file'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    s3_key = db.Column(db.String(512), nullable=False)
    size = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shared_with = db.relationship('SharedFile', backref='file', lazy=True, cascade='all, delete-orphan')

# SharedFile Model
class SharedFile(db.Model):
    __tablename__ = 'shared_file'

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    shared_with_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
