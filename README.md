# 🌩️ Algonive CLOUD-BASED-DOCUMENT-STORAGE-SHARING

A secure and scalable cloud-based document management system built with Flask, AWS services, and a modern UI for uploading, sharing, and managing documents.

![Dashboard Screenshot](assets/Screenshot_dashboard.png)
![Profile Screenshot](assets/Screenshot_profile.png)
![Sign Up](assets/Screenshot_signup.png)
![Sign In](assets/Screenshot_signin.png)

---

## 🚀 Features

- 🔒 Secure Authentication using AWS Cognito
- 📤 Drag-and-drop file upload to Amazon S3
- 👥 Share files with other users by email or username
- 🔐 Generate secure, pre-signed download links
- 🧾 File rename, delete, and view
- 📊 User profile with file statistics
- 📚 User-specific file dashboard
- 📈 Integrated logging with AWS CloudWatch

---

## 🛠️ Tech Stack

| Layer          | Tools Used                                 |
|----------------|---------------------------------------------|
| Backend        | Python, Flask, SQLAlchemy, Flask-Cognito    |
| Frontend       | HTML, CSS (Bootstrap), JavaScript           |
| Database       | PostgreSQL (via AWS RDS)                    |
| File Storage   | Amazon S3                                   |
| Authentication | AWS Cognito                                 |
| Hosting        | AWS EC2                                     |
| Monitoring     | AWS CloudWatch                              |
| Permissions    | AWS IAM                                     |

---

## 🖼️ UI Screenshots

### 📂 Dashboard (Drag & Drop Upload + Sharing)
![Dashboard](assets/Screenshot_dashboard.png)

### 👤 Profile Page (Statistics + User Info)
![Profile](assets/Screenshot_profile.png)

### 🔐 Cognito Hosted Sign Up
![Signup](assets/Screenshot_signup.png)

### 🔑 Cognito Login
![Signin](assets/Screenshot_signin.png)

---
### 🧠 AWS Services Used
Service	Purpose
🗄️ S3	Store user-uploaded documents
🧠 Cognito	User authentication & OAuth handling
📊 RDS	Store metadata, user & file info
💻 EC2	Host Flask application
📜 CloudWatch	Logging file events & application logs
🔐 IAM	Secure access to AWS resources

---
### 📁 Project Structure
```bash
cloud-docs-app/
│
├── app.py
├── models.py
├── templates/
│   ├── dashboard.html
│   ├── profile.html
├── static/
│   ├── style.css
│   └── favicon.ico
├── assets/
│   ├── Screenshot_dashboard.png
│   ├── Screenshot_profile.png
│   ├── Screenshot_signup.png
│   └── Screenshot_signin.png
├── .env
├── requirements.txt
└── README.md
```

---
### 🔧 Setup Instructions (Detailed)

Follow these steps to set up and run the project on your local machine.
## 1️⃣ Clone the Repository

First, you need to get the project code from GitHub to your local machine.

Open your terminal or command prompt and run:

git clone git@github.com:harshit27p/Algonive_CLOUD-BASED-DOCUMENT-STORAGE-SHARING.git
cd Algonive_CLOUD-BASED-DOCUMENT-STORAGE-SHARING

✅ This downloads the entire project folder into your system.

## 2️⃣ Set Up Python Virtual Environment

A virtual environment keeps your project’s dependencies isolated.

Run the following in your terminal:

# Create a virtual environment named "env"
python -m venv env

# Activate the virtual environment:
# On Windows:
env\Scripts\activate

# On MacOS/Linux:
source env/bin/activate

When activated, your terminal should show (env) at the beginning of the line.

## 3️⃣ Install Python Dependencies

Inside the virtual environment, install all required libraries using pip:

pip install -r requirements.txt

📦 This command reads the requirements.txt file and installs Flask, boto3, SQLAlchemy, psycopg2, Flask-Cognito, and other dependencies.

## 4️⃣ Create Environment Variables (.env File)

Create a file named .env in the project root directory. This file stores sensitive information securely and is loaded into your Flask app using libraries like python-dotenv.

Here’s an example of what the .env file should contain:

AWS_ACCESS_KEY_ID=YOUR_AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY=YOUR_AWS_SECRET_KEY
COGNITO_CLIENT_ID=YOUR_COGNITO_CLIENT_ID
COGNITO_CLIENT_SECRET=YOUR_COGNITO_CLIENT_SECRET
COGNITO_DOMAIN=your-cognito-domain.auth.REGION.amazoncognito.com
COGNITO_REDIRECT_URI=http://localhost:5000/callback
S3_BUCKET_NAME=your-s3-bucket-name
DATABASE_URL=postgresql://username:password@host:port/databasename

🔐 Replace the placeholders above with actual credentials:

    You get Cognito credentials from the AWS Cognito User Pool App Client.

    S3 bucket name is your AWS S3 bucket used for file uploads.

    DATABASE_URL is the PostgreSQL URI (from AWS RDS or local setup).

## 5️⃣ Run the Flask App

Once everything is set up, start your app:

python app.py

You should see output like:

 * Running on http://127.0.0.1:5000

🌐 Now open your browser and go to:

http://localhost:5000

You’ll be redirected to the Cognito login screen. After logging in, you’ll be taken to your dashboard.

---
### ✅ Summary of What’s Happening

    📂 Files you upload go to your S3 bucket.

    🧑 Auth is handled securely via AWS Cognito Hosted UI.

    🗃️ Metadata (user info, file info, share info) is stored in PostgreSQL (via RDS).

    📈 Activity is logged using AWS CloudWatch for observability.

    💻 Flask app is hosted locally now, but can be deployed to AWS EC2 for production.





