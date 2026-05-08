"""
Consumer bounded-context API routes.

This module registers all consumer sub-blueprints. Route implementations
live in domain-specific sub-modules:
  - consumer_summary.py: summary, channel, propagation paths
  - consumer_branch.py: branches, interventions, comparison, resume/status
  - consumer_comparison.py: comparison snapshots CRUD
  - consumer_asset.py: research assets, research actions
  - consumer_interview.py: interviews, focus groups, representative agents
  - consumer_misc.py: run estimate, audit chain, dead letters, personas
"""

from flask import Blueprint

from . import consumer_bp
from .consumer_summary import consumer_summary_bp
from .consumer_branch import consumer_branch_bp
from .consumer_comparison import consumer_comparison_bp
from .consumer_asset import consumer_asset_bp
from .consumer_interview import consumer_interview_bp
from .consumer_misc import consumer_misc_bp


def register_consumer_routes(app):
    """Register all consumer sub-blueprints."""
    app.register_blueprint(consumer_summary_bp)
    app.register_blueprint(consumer_branch_bp)
    app.register_blueprint(consumer_comparison_bp)
    app.register_blueprint(consumer_asset_bp)
    app.register_blueprint(consumer_interview_bp)
    app.register_blueprint(consumer_misc_bp)
