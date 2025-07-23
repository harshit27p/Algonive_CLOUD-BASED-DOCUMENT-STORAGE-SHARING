from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    users = [
        User(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('admin123')
        ),
        User(
            username='alice',
            email='alice@example.com',
            password=generate_password_hash('alice123')
        ),
        User(
            username='bob',
            email='bob@example.com',
            password=generate_password_hash('bob123')
        )
    ]

    for user in users:
        if not User.query.filter_by(username=user.username).first():
            db.session.add(user)

    db.session.commit()
    print("Seeded users: admin, alice, bob")
