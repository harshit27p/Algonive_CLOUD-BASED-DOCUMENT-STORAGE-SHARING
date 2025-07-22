from app import db, User
from werkzeug.security import generate_password_hash

with db.session.begin():
    db.session.add_all([
        User(username='admin', password=generate_password_hash('admin')),
        User(username='alice', password=generate_password_hash('alice')),
        User(username='bob', password=generate_password_hash('bob')),
    ])
print("Users seeded")