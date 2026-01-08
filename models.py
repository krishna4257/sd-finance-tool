from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Enum as SAEnum,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from db import Base


# =========================
# ENUM DEFINITIONS
# =========================

class EmployeeLevel(str, Enum):
    employee = "employee"
    accounts = "accounts"
    admin = "admin"
    master = "master"
    partner = "partner"


class PaymentType(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class UserRole(str, Enum):
    employee = "employee"
    accounts = "accounts"
    admin = "admin"
    master = "master"
    partner = "partner"


# =========================
# VILLAGE
# =========================

class Village(Base):
    __tablename__ = "village"

    vid = Column(Integer, primary_key=True)
    vname = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    employees = relationship("Employee", back_populates="village")
    customers = relationship("Customer", back_populates="village")

    def __repr__(self):
        return f"<Village vid={self.vid} name={self.vname}>"


# =========================
# EMPLOYEE
# =========================

class Employee(Base):
    __tablename__ = "emp"

    eid = Column(Integer, primary_key=True)
    ename = Column(String(100), nullable=False)
    level = Column(SAEnum(EmployeeLevel), nullable=False)

    vid = Column(Integer, ForeignKey("village.vid"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    village = relationship("Village", back_populates="employees")
    customers = relationship("Customer", back_populates="employee")

    def __repr__(self):
        return f"<Employee eid={self.eid} name={self.ename} level={self.level}>"

# =========================
# CUSTOMER
# =========================

class Customer(Base):
    __tablename__ = "customer"

    cid = Column(Integer, primary_key=True)
    ano = Column(Integer, nullable=False)  # employee-facing account number

    name = Column(String(150), nullable=False)

    vid = Column(Integer, ForeignKey("village.vid"), nullable=False)
    eid = Column(Integer, ForeignKey("emp.eid"), nullable=True)

    pano = Column(Integer, nullable=True)
    aadhaar = Column(String(16), nullable=True)

    fdt = Column(Date, nullable=True)
    tdt = Column(Date, nullable=True)

    amt = Column(Numeric(12, 2), nullable=True)
    pamt = Column(Numeric(12, 2), nullable=True)
    bamt = Column(Numeric(12, 2), nullable=True)
    iamt = Column(Numeric(12, 2), nullable=True)

    type = Column(SAEnum(PaymentType), nullable=True)
    period = Column(Integer, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint("vid", "ano", name="uq_customer_village_ano"),
    )

    # Relationships
    village = relationship("Village", back_populates="customers")
    employee = relationship("Employee", back_populates="customers")
    payments = relationship(
        "Payment",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Customer cid={self.cid} ano={self.ano} name={self.name}>"

# =========================
# PAYMENT
# =========================

class Payment(Base):
    __tablename__ = "payment"

    pid = Column(Integer, primary_key=True)

    cid = Column(Integer, ForeignKey("customer.cid"), nullable=False)
    vid = Column(Integer, ForeignKey("village.vid"), nullable=False)

    ano = Column(Integer, nullable=False)  # employee-facing
    amt = Column(Numeric(12, 2), nullable=False)

    payment_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="payments")
    village = relationship("Village")

    def __repr__(self):
        return f"<Payment pid={self.pid} ano={self.ano} amt={self.amt}>"

# =========================
# USERS
# =========================

class User(Base):
    __tablename__ = "users"

    uid = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User uid={self.uid} username={self.username} role={self.role}>"