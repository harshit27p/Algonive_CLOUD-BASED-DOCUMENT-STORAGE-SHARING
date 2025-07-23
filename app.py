from flask import Flask, render_template, request, redirect, flash, jsonify, session, url_for
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db, User, File, SharedFile
from datetime import datetime, timezone
import boto3
import os
import logging
import watchtower
import requests
from jose import jwt, JWTError
from dotenv import load_dotenv
from config import Config
from functools import wraps
from urllib.parse import urlencode
from sqlalchemy import or_
from datetime import timedelta
from flask_migrate import Migrate

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
db.init_app(app)

migrate = Migrate(app, db)

# AWS S3
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

# CloudWatch logging
LOG_GROUP = "/algonive/flask"
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(watchtower.CloudWatchLogHandler(log_group=LOG_GROUP))

# Cognito
COGNITO_DOMAIN = os.getenv("COGNITO_DOMAIN")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID")
COGNITO_CLIENT_SECRET = os.getenv("COGNITO_CLIENT_SECRET")
COGNITO_REDIRECT_URI = os.getenv("COGNITO_REDIRECT_URI")

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'id_token' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect('/dashboard')

@app.route('/login')
def login():
    query = urlencode({
        "response_type": "code",
        "client_id": COGNITO_CLIENT_ID,
        "redirect_uri": COGNITO_REDIRECT_URI,
        "scope": "openid email profile"
    })
    return redirect(f"{COGNITO_DOMAIN}/oauth2/authorize?{query}")

@app.route('/callback')
def callback():
    code = request.args.get("code")
    if not code:
        return "Missing authorization code from Cognito", 400

    token_url = f"{COGNITO_DOMAIN}/oauth2/token"
    auth = (COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": COGNITO_REDIRECT_URI
    }

    try:
        response = requests.post(token_url, data=body, auth=auth, headers=headers)
        token_data = response.json()
        id_token = token_data.get("id_token")
        if not id_token:
            return f"Failed to get id_token. Response: {token_data}", 400

        claims = jwt.get_unverified_claims(id_token)
        session['id_token'] = id_token
        session['username'] = claims.get("cognito:username").lower()
        session['email'] = claims.get("email")

        user = db.session.query(User).filter(or_(User.username == session['username'], User.email == session['email'])).first()
        if not user:
            user = User(username=session['username'], email=session['email'], password="cognito")
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"User creation failed in callback: {e}")
        session['user_id'] = user.id
        logger.info(f"User '{session['username']}' logged in via Cognito")
        return redirect('/dashboard')
    except Exception as e:
        logger.error(f"Callback processing failed: {e}")
        return f"Callback error: {str(e)}", 500

@app.route('/logout')
def logout():
    username = session.get("username", "Anonymous")
    session.clear()
    logger.info(f"User '{username}' logged out.")

    logout_url = f"{COGNITO_DOMAIN}/logout?" + urlencode({
        "client_id": COGNITO_CLIENT_ID,
        "logout_uri": url_for('login', _external=True)
    })
    return redirect(logout_url)

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    files = File.query.filter_by(owner_id=user.id).all() if user else []
    shared_files = SharedFile.query.filter_by(shared_with_id=user.id).all() if user else []
    recent_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
    # Normalize all file.uploaded_at values to be timezone-aware
    for f in files:
    	if f.uploaded_at and f.uploaded_at.tzinfo is None:
        	f.uploaded_at = f.uploaded_at.replace(tzinfo=timezone.utc)
    return render_template('dashboard.html', files=files, shared_files=shared_files, user=user, recent_threshold=recent_threshold)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect('/dashboard')

    file = request.files.get('file')
    if not file:
        flash("No file selected for upload", "warning")
        return redirect('/dashboard')

    filename = secure_filename(file.filename)
    key = f"{session['username']}/{filename}"
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    try:
        s3.upload_fileobj(file, BUCKET, key)
        new_file = File(
            filename=filename,
            s3_key=key,
            owner_id=user.id,
            size=size,
            uploaded_at=datetime.now(timezone.utc)
        )
        db.session.add(new_file)
        db.session.commit()
        logger.info(f"User '{user.username}' uploaded file: {filename} ({size} bytes)")
        flash("File uploaded successfully", "success")
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        flash("An error occurred during upload.", "danger")

    return redirect('/dashboard')

@app.route('/generate-link', methods=['POST'])
@login_required
def generate_link():
    filename = request.form['filename']
    prefix = request.form.get('prefix', session['username'])
    key = f"{prefix}/{filename}"
    try:
        url = s3.generate_presigned_url('get_object', Params={'Bucket': BUCKET, 'Key': key}, ExpiresIn=3600)
        return jsonify({'url': url})
    except Exception as e:
        logger.error(f"Error generating link for {filename}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete/<int:file_id>')
@login_required
def delete_file(file_id):
    file = db.session.get(File, file_id)
    if file and file.owner_id == session['user_id']:
        try:
            s3.delete_object(Bucket=BUCKET, Key=file.s3_key)
            db.session.delete(file)
            db.session.commit()
            flash("File deleted.", "success")
        except Exception as e:
            db.session.rollback()
            logger.error(f"File deletion failed: {str(e)}")
            flash("Could not delete file.", "danger")
    return redirect('/dashboard')

@app.route('/rename', methods=['POST'])
@login_required
def rename():
    file_id = request.form.get('file_id')
    new_name = secure_filename(request.form.get('new_name'))
    file = db.session.get(File, int(file_id))
    if file and file.owner_id == session['user_id']:
        new_key = f"{session['username']}/{new_name}"
        try:
            s3.copy_object(Bucket=BUCKET, CopySource={"Bucket": BUCKET, "Key": file.s3_key}, Key=new_key)
            s3.delete_object(Bucket=BUCKET, Key=file.s3_key)
            file.filename = new_name
            file.s3_key = new_key
            db.session.commit()
            flash("File renamed.", "success")
        except Exception as e:
            logger.error(f"Rename failed: {str(e)}")
            flash("Rename failed.", "danger")
    return redirect('/dashboard')

@app.route('/share', methods=['POST'])
@login_required
def share():
    recipient_input = request.form['recipient']
    filename = request.form['filename']
    file = File.query.filter_by(filename=filename, owner_id=session['user_id']).first()
    recipient = User.query.filter(or_(User.username == recipient_input.lower(), User.email == recipient_input)).first()
    if file and recipient:
        shared = SharedFile(file_id=file.id, shared_with_id=recipient.id)
        db.session.add(shared)
        db.session.commit()
        flash("File shared successfully.", "success")
    else:
        flash("Sharing failed. Check file and recipient.", "danger")
    return redirect('/dashboard')

@app.route('/revoke/<int:file_id>/<int:user_id>', methods=['POST'])
@login_required
def revoke(file_id, user_id):
    shared = SharedFile.query.filter_by(file_id=file_id, shared_with_id=user_id).first()
    if shared:
        db.session.delete(shared)
        db.session.commit()
        flash("Access revoked.", "success")
    else:
        flash("Revoke failed.", "danger")
    return redirect('/dashboard')

@app.route('/profile')
@login_required
def profile():
    user = db.session.get(User, session['user_id'])
    shared_with_me = SharedFile.query.filter_by(shared_with_id=user.id).all()
    shared_by_user = SharedFile.query.join(File).filter(File.owner_id == user.id).all()

    return render_template(
        'profile.html',
        user=user,
        shared_with_me=shared_with_me,
        shared_by_user=shared_by_user
    )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
