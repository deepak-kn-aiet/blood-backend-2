"""
Database Seeder Module

Populates PostgreSQL with realistic Indian/Bangalore data for development and hackathon demos.
Generates Users, Donors, Hospitals, Blood Banks, Inventories, and Emergency Requests.

Usage:
    python -m app.seed
"""

import random
from datetime import datetime, timedelta, timezone
from typing import List
from faker import Faker

from app.database import engine, Base, SessionLocal
from app.models import (
    User,
    Donor,
    Hospital,
    BloodBank,
    BloodInventory,
    EmergencyRequest,
)
from app.enums import (
    RoleEnum,
    BloodGroupEnum,
    RequestStatusEnum,
)
from app.auth import get_password_hash

# Initialize Faker with Indian locale
fake = Faker("en_IN")

# Constants & Pre-defined realistic Bangalore locations
BANGALORE_CITIES = [
    "Bangalore",
    "Whitefield",
    "Indiranagar",
    "Koramangala",
    "Jayanagar",
    "Electronic City",
    "HSR Layout",
    "Yelahanka",
]

BANGALORE_HOSPITAL_NAMES = [
    "Manipal Hospital Whitefield",
    "Fortis Hospital Bannerghatta",
    "Apollo Hospital Jayanagar",
    "Aster CMI Hospital Yelahanka",
    "Columbia Asia Hospital Hebbal",
    "St. John's Medical College Hospital",
    "Narayana Health City",
    "BGS Gleneagles Global Hospital",
    "Sakra World Hospital Marathahalli",
    "Cloudnine Hospital Old Airport Road",
]

BLOOD_BANK_NAMES = [
    "Rotary TTK Blood Bank Bangalore",
    "Lions Blood Bank Koramangala",
    "Red Cross Blood Centre Indiranagar",
    "Rashtrotthana Blood Centre Jayanagar",
    "Narayana Blood Centre Electronic City",
]

ALL_BLOOD_GROUPS = [
    BloodGroupEnum.A_POSITIVE,
    BloodGroupEnum.A_NEGATIVE,
    BloodGroupEnum.B_POSITIVE,
    BloodGroupEnum.B_NEGATIVE,
    BloodGroupEnum.AB_POSITIVE,
    BloodGroupEnum.AB_NEGATIVE,
    BloodGroupEnum.O_POSITIVE,
    BloodGroupEnum.O_NEGATIVE,
]


def seed_database():
    """
    Executes database seeding if the database is currently empty.
    Creates schema tables automatically if required.
    """
    # Ensure database schema tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check if database is already seeded
        existing_users_count = db.query(User).count()
        if existing_users_count > 0:
            print("Database already seeded.")
            return

        print("Starting Blood Relay Database Seeding...")

        # Shared password hash for all demo seed accounts
        hashed_pw = get_password_hash("password123")

        # ----------------------------------------------------
        # 1. Generate 50 Users (35 Citizens, 10 Hospitals, 5 Blood Banks)
        # ----------------------------------------------------
        citizen_users: List[User] = []
        hospital_users: List[User] = []
        blood_bank_users: List[User] = []

        used_emails = set()
        used_phones = set()

        def generate_unique_contact():
            while True:
                email = fake.email()
                phone = f"+91{random.randint(6000000000, 9999999999)}"
                if email not in used_emails and phone not in used_phones:
                    used_emails.add(email)
                    used_phones.add(phone)
                    return email, phone

        # Generate 35 Citizen Users
        for _ in range(35):
            email, phone = generate_unique_contact()
            u = User(
                full_name=fake.name(),
                email=email,
                phone_number=phone,
                password_hash=hashed_pw,
                role=RoleEnum.CITIZEN,
                is_active=True,
            )
            citizen_users.append(u)

        # Generate 10 Hospital Users
        for i in range(10):
            email, phone = generate_unique_contact()
            u = User(
                full_name=f"{BANGALORE_HOSPITAL_NAMES[i]} Admin",
                email=email,
                phone_number=phone,
                password_hash=hashed_pw,
                role=RoleEnum.HOSPITAL,
                is_active=True,
            )
            hospital_users.append(u)

        # Generate 5 Blood Bank Users
        for i in range(5):
            email, phone = generate_unique_contact()
            u = User(
                full_name=f"{BLOOD_BANK_NAMES[i]} Manager",
                email=email,
                phone_number=phone,
                password_hash=hashed_pw,
                role=RoleEnum.BLOOD_BANK,
                is_active=True,
            )
            blood_bank_users.append(u)

        # Add all users to session and commit
        db.add_all(citizen_users + hospital_users + blood_bank_users)
        db.commit()

        # Refresh instances to populate generated UUID primary keys
        for u in citizen_users + hospital_users + blood_bank_users:
            db.refresh(u)

        # ----------------------------------------------------
        # 2. Generate 35 Donor Profiles (Linked to 35 Citizen Users)
        # ----------------------------------------------------
        donors: List[Donor] = []
        now_utc = datetime.now(timezone.utc)

        for u in citizen_users:
            # Coordinates around Bangalore (12.9716, 77.5946)
            lat = round(12.9716 + random.uniform(-0.15, 0.15), 6)
            lon = round(77.5946 + random.uniform(-0.15, 0.15), 6)
            is_avail = random.random() < 0.8  # 80% available
            resp_rate = round(random.uniform(60.0, 100.0), 1)
            days_ago = random.randint(60, 250)
            last_donated = now_utc - timedelta(days=days_ago)

            d = Donor(
                user_id=u.id,
                blood_group=random.choice(ALL_BLOOD_GROUPS),
                city=random.choice(BANGALORE_CITIES),
                latitude=lat,
                longitude=lon,
                is_available=is_avail,
                last_donation_date=last_donated,
                response_rate=resp_rate,
                health_status="Eligible for donation",
            )
            donors.append(d)

        db.add_all(donors)

        # ----------------------------------------------------
        # 3. Generate 10 Hospital Profiles (Linked to Hospital Users)
        # ----------------------------------------------------
        hospitals: List[Hospital] = []
        for i, hu in enumerate(hospital_users):
            lat = round(12.9716 + random.uniform(-0.12, 0.12), 6)
            lon = round(77.5946 + random.uniform(-0.12, 0.12), 6)

            h = Hospital(
                user_id=hu.id,
                hospital_name=BANGALORE_HOSPITAL_NAMES[i],
                address=f"{random.randint(10, 999)}, {random.choice(BANGALORE_CITIES)}, Bangalore, Karnataka",
                latitude=lat,
                longitude=lon,
                contact_number=hu.phone_number,
            )
            hospitals.append(h)

        db.add_all(hospitals)

        # ----------------------------------------------------
        # 4. Generate 5 Blood Banks
        # ----------------------------------------------------
        blood_banks: List[BloodBank] = []
        for i in range(5):
            lat = round(12.9716 + random.uniform(-0.10, 0.10), 6)
            lon = round(77.5946 + random.uniform(-0.10, 0.10), 6)

            bb = BloodBank(
                name=BLOOD_BANK_NAMES[i],
                address=f"{random.randint(1, 100)} Main Road, {random.choice(BANGALORE_CITIES)}, Bangalore, Karnataka",
                latitude=lat,
                longitude=lon,
                contact_number=blood_bank_users[i].phone_number,
            )
            blood_banks.append(bb)

        db.add_all(blood_banks)
        db.commit()

        # Refresh Hospitals and Blood Banks to acquire generated UUIDs
        for h in hospitals:
            db.refresh(h)
        for bb in blood_banks:
            db.refresh(bb)

        # ----------------------------------------------------
        # 5. Generate 200 Blood Inventory Records
        # ----------------------------------------------------
        inventories: List[BloodInventory] = []
        for _ in range(200):
            target_bb = random.choice(blood_banks)
            bg = random.choice(ALL_BLOOD_GROUPS)
            units = random.randint(5, 50)
            exp_days = random.randint(10, 60)
            exp_date = now_utc + timedelta(days=exp_days)

            inv = BloodInventory(
                blood_bank_id=target_bb.id,
                blood_group=bg,
                units_available=units,
                expiry_date=exp_date,
            )
            inventories.append(inv)

        db.add_all(inventories)

        # ----------------------------------------------------
        # 6. Generate 20 Emergency Requests
        # ----------------------------------------------------
        requests_list: List[EmergencyRequest] = []
        statuses = [
            RequestStatusEnum.PENDING,
            RequestStatusEnum.SEARCHING,
            RequestStatusEnum.MATCHED,
            RequestStatusEnum.COMPLETED,
        ]

        for _ in range(20):
            hosp = random.choice(hospitals)
            bg = random.choice(ALL_BLOOD_GROUPS)
            req = EmergencyRequest(
                patient_name=fake.name(),
                blood_group=bg,
                units_required=random.randint(1, 5),
                hospital_id=hosp.id,
                latitude=hosp.latitude,
                longitude=hosp.longitude,
                status=random.choice(statuses),
            )
            requests_list.append(req)

        db.add_all(requests_list)
        db.commit()

        # Final Summary Output
        print("\n=========================================")
        print("Blood Relay Seeder")
        print("=========================================")
        print(f"Users: {len(citizen_users) + len(hospital_users) + len(blood_bank_users)}")
        print(f"Donors: {len(donors)}")
        print(f"Hospitals: {len(hospitals)}")
        print(f"Blood Banks: {len(blood_banks)}")
        print(f"Inventory: {len(inventories)}")
        print(f"Emergency Requests: {len(requests_list)}")
        print("\nSeed Complete Successfully")
        print("=========================================\n")

    except Exception as e:
        db.rollback()
        print(f"Seeding failed: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
