from sqlalchemy.exc import IntegrityError
import faker

from . import db
from .models import User, Post

import random


def create_users(count=100):
    fake = faker.Faker()
    i = 0
    while i < count:
        u = User(email=fake.email(),
                username=fake.user_name(),
                password="password",
                confirmed=True,
                name=fake.name(),
                location=fake.city(),
                about_me=fake.text(),
                member_since=fake.past_date()
        )
        db.session.add(u)
        i += 1
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        

def create_posts(count=100):
    fake=faker.Faker()
    user_count = User.query.count()
    for _ in range(count):
        u = User.query.offset(random.randint(2, user_count-1)).first()
        p = Post(body=fake.text(),
                timestamp=fake.past_date(),
                author=u
        )
        db.session.add(p)
    db.session.commit()
