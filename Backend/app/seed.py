from app.database.database import SessionLocal
from app.models.user import User
from app.enums.user import UserRole, UserStatus
from app.services.auth_service import hash_password


def create_user_if_not_exists(
    db,
    name: str,
    email: str,
    password: str,
    role: UserRole
):
    existing_user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_user:
        print(f"{email} already exists.")

        # Update existing user for local/dev testing
        existing_user.name = name
        existing_user.password_hash = hash_password(password)
        existing_user.role = role
        existing_user.status = UserStatus.ACTIVE

        db.commit()
        db.refresh(existing_user)

        print(
            f"Updated {role.value}: "
            f"{existing_user.email} (ID: {existing_user.id})"
        )

        return

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        status=UserStatus.ACTIVE
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    print(
        f"Created {role.value}: "
        f"{user.email} (ID: {user.id})"
    )

def main():
    db = SessionLocal()

    try:
        create_user_if_not_exists(
            db=db,
            name="Test Agent",
            email="agent@test.com",
            password="12345678",
            role=UserRole.AGENT
        )

        create_user_if_not_exists(
            db=db,
            name="Test Admin",
            email="admin@test.com",
            password="12345678",
            role=UserRole.ADMIN
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()