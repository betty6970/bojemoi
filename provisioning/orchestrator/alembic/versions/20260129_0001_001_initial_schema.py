"""Initial schema - deployments and deployment_blocks tables

Revision ID: 001
Revises: None
Create Date: 2026-01-29

This migration creates the initial database schema for the Bojemoi Orchestrator:
- deployments: Traditional deployment tracking table
- deployment_blocks: Blockchain audit trail table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables and indexes."""

    # =========================================================================
    # DEPLOYMENTS TABLE
    # Traditional deployment tracking for backward compatibility
    # =========================================================================
    op.create_table(
        'deployments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False, comment='Deployment type: vm, container'),
        sa.Column('name', sa.String(255), nullable=False, comment='Deployment name'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Configuration as JSON'),
        sa.Column('resource_ref', sa.String(255), nullable=True, comment='XenServer VM ref or Docker service ID'),
        sa.Column('status', sa.String(50), nullable=False, comment='Status: pending, running, success, failed'),
        sa.Column('error', sa.Text(), nullable=True, comment='Error message if failed'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for deployments table
    op.create_index('idx_deployments_type', 'deployments', ['type'])
    op.create_index('idx_deployments_status', 'deployments', ['status'])
    op.create_index('idx_deployments_name', 'deployments', ['name'])
    op.create_index('idx_deployments_created_at', 'deployments', ['created_at'])

    # =========================================================================
    # DEPLOYMENT_BLOCKS TABLE (Blockchain)
    # Immutable audit trail using SHA-256 hash chain
    # =========================================================================
    op.create_table(
        'deployment_blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('block_number', sa.BigInteger(), nullable=False, comment='Block number in chain (0 = genesis)'),
        sa.Column('previous_hash', sa.String(64), nullable=True, comment='SHA-256 hash of previous block'),
        sa.Column('current_hash', sa.String(64), nullable=False, comment='SHA-256 hash of this block'),

        # Deployment data
        sa.Column('deployment_type', sa.String(50), nullable=False, comment='Type: genesis, vm, container'),
        sa.Column('name', sa.String(255), nullable=False, comment='Deployment name'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Configuration snapshot'),
        sa.Column('resource_ref', sa.String(255), nullable=True, comment='Resource reference'),
        sa.Column('status', sa.String(50), nullable=False, comment='Deployment status'),
        sa.Column('error', sa.Text(), nullable=True, comment='Error message if failed'),

        # Audit fields
        sa.Column('source_ip', sa.String(45), nullable=True, comment='Source IP (IPv4/IPv6)'),
        sa.Column('source_country', sa.String(10), nullable=True, comment='ISO country code'),

        # Timestamp
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('block_number', name='uq_block_number'),
        sa.UniqueConstraint('current_hash', name='uq_current_hash'),
        sa.CheckConstraint('LENGTH(current_hash) = 64', name='ck_hash_length')
    )

    # Indexes for deployment_blocks table
    op.create_index('idx_blocks_number', 'deployment_blocks', ['block_number'])
    op.create_index('idx_blocks_hash', 'deployment_blocks', ['current_hash'])
    op.create_index('idx_blocks_type', 'deployment_blocks', ['deployment_type'])
    op.create_index('idx_blocks_status', 'deployment_blocks', ['status'])
    op.create_index('idx_blocks_name', 'deployment_blocks', ['name'])
    op.create_index('idx_blocks_created_at', 'deployment_blocks', ['created_at'])
    op.create_index('idx_blocks_source_ip', 'deployment_blocks', ['source_ip'])
    op.create_index('idx_blocks_source_country', 'deployment_blocks', ['source_country'])

    # =========================================================================
    # COMMENTS
    # =========================================================================
    # Add table comments
    op.execute("COMMENT ON TABLE deployments IS 'Deployment records for VMs and containers'")
    op.execute("COMMENT ON TABLE deployment_blocks IS 'Blockchain audit trail with SHA-256 hash chain'")


def downgrade() -> None:
    """Drop all tables and indexes."""

    # Drop deployment_blocks table and indexes
    op.drop_index('idx_blocks_source_country', table_name='deployment_blocks')
    op.drop_index('idx_blocks_source_ip', table_name='deployment_blocks')
    op.drop_index('idx_blocks_created_at', table_name='deployment_blocks')
    op.drop_index('idx_blocks_name', table_name='deployment_blocks')
    op.drop_index('idx_blocks_status', table_name='deployment_blocks')
    op.drop_index('idx_blocks_type', table_name='deployment_blocks')
    op.drop_index('idx_blocks_hash', table_name='deployment_blocks')
    op.drop_index('idx_blocks_number', table_name='deployment_blocks')
    op.drop_table('deployment_blocks')

    # Drop deployments table and indexes
    op.drop_index('idx_deployments_created_at', table_name='deployments')
    op.drop_index('idx_deployments_name', table_name='deployments')
    op.drop_index('idx_deployments_status', table_name='deployments')
    op.drop_index('idx_deployments_type', table_name='deployments')
    op.drop_table('deployments')
