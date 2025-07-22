from flask import Flask, render_template, request, redirect, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
import boto3
import os

# Load environment variables
load_dotenv()

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
BUCKET = os.getenv("AWS_BUCKET_NAME")

# Initialize Flask
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")

# AWS S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com"
)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Dummy users
dummy_users = {
    "admin": {"password": "admin"},
    "alice": {"password": "alice"},
    "bob": {"password": "bob"}
}

# In-memory file sharing structure
shared_files = {}  # Format: shared_files = {"bob": ["admin/filename"]}

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in dummy_users and dummy_users[username]['password'] == password:
            login_user(User(username))
            return redirect('/dashboard')
        else:
            flash("Invalid username or password")
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=f"{current_user.id}/")
    owned = response.get('Contents', [])
    owned_files = [
        {
            'filename': f['Key'].split('/')[-1],
            'filesize': f['Size'],
            'uploaded_at': f['LastModified'],
            'id': f['Key']  # used for rename/delete
        } for f in owned
    ]
    shared = shared_files.get(current_user.id, [])
    shared_display = [{'filename': s.split('/')[-1], 's3_key': s} for s in shared]
    return render_template('dashboard.html', user=current_user.id, files=owned_files, shared_files=shared_display)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files['file']
    if file:
        key = f"{current_user.id}/{file.filename}"
        s3.upload_fileobj(file, BUCKET, key)
        flash("File uploaded successfully.")
    return redirect('/dashboard')

@app.route('/rename', methods=['POST'])
@login_required
def rename():
    file_id = request.form['file_id']
    new_name = request.form['new_name']
    new_key = f"{current_user.id}/{new_name}"
    try:
        s3.copy_object(Bucket=BUCKET, CopySource=f"{BUCKET}/{file_id}", Key=new_key)
        s3.delete_object(Bucket=BUCKET, Key=file_id)
        flash("File renamed.")
    except Exception as e:
        flash(f"Error renaming file: {str(e)}")
    return redirect('/dashboard')

@app.route('/delete/<path:file_id>')
@login_required
def delete(file_id):
    try:
        s3.delete_object(Bucket=BUCKET, Key=file_id)
        flash("File deleted.")
    except Exception as e:
        flash(f"Error deleting file: {str(e)}")
    return redirect('/dashboard')

@app.route('/share', methods=['POST'])
@login_required
def share():
    recipient = request.form['recipient']
    filename = request.form['filename']
    key = f"{current_user.id}/{filename}"

    if recipient in dummy_users and recipient != current_user.id:
        shared_files.setdefault(recipient, []).append(key)
        flash(f"File shared with {recipient}")
    else:
        flash("Invalid recipient")
    return redirect('/dashboard')

@app.route('/generate-link', methods=['POST'])
@login_required
def generate_link():
    filename = request.form['filename']
    prefix = request.form.get('prefix', current_user.id)
    key = f"{prefix}/{filename}"

    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET, 'Key': key},
            ExpiresIn=3600
        )
        return jsonify({"url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
