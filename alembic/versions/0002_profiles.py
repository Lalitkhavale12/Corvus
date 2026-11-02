"""profiles

Revision ID: 0002_profiles
Revises: 0001_initial
Create Date: 2026-10-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_profiles"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_profiles",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("date_of_birth", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sex", sa.String(length=10), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("mrn", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_patient_profiles_mrn"), "patient_profiles", ["mrn"], unique=True)
    op.create_index(op.f("ix_patient_profiles_user_id"), "patient_profiles", ["user_id"])

    op.create_table(
        "doctor_profiles",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("license_number", sa.String(length=50), nullable=True),
        sa.Column("specialization", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_doctor_profiles_license_number"), "doctor_profiles", ["license_number"], unique=True)
    op.create_index(op.f("ix_doctor_profiles_user_id"), "doctor_profiles", ["user_id"])

    op.create_table(
        "patient_doctor_mapping",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "patient_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "doctor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patient_doctor_mapping_doctor_id"), "patient_doctor_mapping", ["doctor_id"])
    op.create_index(op.f("ix_patient_doctor_mapping_id"), "patient_doctor_mapping", ["id"])
    op.create_index(op.f("ix_patient_doctor_mapping_patient_id"), "patient_doctor_mapping", ["patient_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_patient_doctor_mapping_patient_id"), table_name="patient_doctor_mapping")
    op.drop_index(op.f("ix_patient_doctor_mapping_id"), table_name="patient_doctor_mapping")
    op.drop_index(op.f("ix_patient_doctor_mapping_doctor_id"), table_name="patient_doctor_mapping")
    op.drop_table("patient_doctor_mapping")
    op.drop_index(op.f("ix_doctor_profiles_user_id"), table_name="doctor_profiles")
    op.drop_index(op.f("ix_doctor_profiles_license_number"), table_name="doctor_profiles")
    op.drop_table("doctor_profiles")
    op.drop_index(op.f("ix_patient_profiles_user_id"), table_name="patient_profiles")
    op.drop_index(op.f("ix_patient_profiles_mrn"), table_name="patient_profiles")
    op.drop_table("patient_profiles")
