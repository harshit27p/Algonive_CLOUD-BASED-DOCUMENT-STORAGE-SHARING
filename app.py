from flask import Flask, render_template, request, redirect, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from flask_bcrypt import Bcrypt
from models import db, User, File, SharedFile
from datetime import datetime
from werkzeug.utils import secure_filename
import boto3
import os
from dotenv import load_dotenv
from config import Config

# Load environment variables
load_dotenv()

# Flask app setup
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
bcrypt = Bcrypt(app)

# AWS S3 setup
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
BUCKET = os.getenv("AWS_BUCKET_NAME")

s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com"
)

# Flask-Login setup
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_username = request.form.get('email_or_username')
        password = request.form['password']
        user = User.query.filter((User.email == email_or_username) | (User.username == email_or_username)).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect('/dashboard')
        flash("Invalid credentials")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists")
            return redirect('/register')
        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please login.")
        return redirect('/login')
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    files = File.query.filter_by(owner_id=current_user.id).all()
    shared_files = SharedFile.query.filter_by(shared_with_id=current_user.id).all()
    return render_template('dashboard.html', files=files, shared_files=shared_files, user=current_user)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        key = f"{current_user.username}/{filename}"

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)  # rewind file pointer back to beginning

        s3.upload_fileobj(file, BUCKET, key)

        new_file = File(
            filename=filename,
            s3_key=key,
            owner_id=current_user.id,
            size=size,
            uploaded_at=datetime.utcnow()
        )
        db.session.add(new_file)
        db.session.commit()
        flash("File uploaded successfully", "success")
    return redirect('/dashboard')

@app.route('/delete/<int:file_id>', methods=['GET'])
@login_required
def delete_file(file_id):
    file = File.query.get(file_id)
    if file and file.owner_id == current_user.id:
        try:
            s3.delete_object(Bucket=BUCKET, Key=file.s3_key)
            db.session.delete(file)
            db.session.commit()
            flash("File deleted successfully")
        except Exception as e:
            flash(f"Error deleting file: {str(e)}")
    return redirect('/dashboard')

@app.route('/rename', methods=['POST'])
@login_required
def rename_file():
    file_id = request.form['file_id']
    new_name = request.form['new_name']
    file = File.query.get(file_id)
    if file and file.owner_id == current_user.id:
        new_key = f"{current_user.username}/{new_name}"
        try:
            s3.copy_object(Bucket=BUCKET, CopySource={'Bucket': BUCKET, 'Key': file.s3_key}, Key=new_key)
            s3.delete_object(Bucket=BUCKET, Key=file.s3_key)
            file.filename = new_name
            file.s3_key = new_key
            db.session.commit()
            flash("File renamed successfully")
        except Exception as e:
            flash(f"Rename failed: {str(e)}")
    return redirect('/dashboard')

@app.route('/generate-link', methods=['POST'])
@login_required
def generate_link():
    filename = request.form['filename']
    prefix = request.form.get('prefix', current_user.username)
    key = f"{prefix}/{filename}"
    try:
        url = s3.generate_presigned_url('get_object', Params={'Bucket': BUCKET, 'Key': key}, ExpiresIn=3600)
        return jsonify({'url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/share', methods=['POST'])
@login_required
def share():
    recipient_input = request.form['recipient']
    filename = request.form['filename']
    recipient = User.query.filter((User.username == recipient_input) | (User.email == recipient_input)).first()
    file = File.query.filter_by(filename=filename, owner_id=current_user.id).first()
    if recipient and file:
        existing = SharedFile.query.filter_by(file_id=file.id, shared_with_id=recipient.id).first()
        if not existing:
            shared = SharedFile(file_id=file.id, shared_with_id=recipient.id)
            db.session.add(shared)
            db.session.commit()
            flash(f"Shared with {recipient.username or recipient.email}")
        else:
            flash("Already shared with this user")
    else:
        flash("Invalid recipient or file")
    return redirect('/dashboard')

@app.route('/revoke/<int:file_id>/<int:user_id>', methods=['POST'])
@login_required
def revoke(file_id, user_id):
    shared = SharedFile.query.filter_by(file_id=file_id, shared_with_id=user_id).first()
    if shared:
        db.session.delete(shared)
        db.session.commit()
        flash("Sharing revoked")
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/login')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
