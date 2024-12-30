from flask import Blueprint, jsonify, render_template
from src.core.database import get_db
from src.utils.decorators import admin_required
from . import services, scheduler

bp = Blueprint('email', __name__, url_prefix='/admin/email')

@bp.route("/monitor")
@admin_required
def monitor():
    """Display email monitoring dashboard."""
    db = next(get_db())
    email_service = services.EmailService(db)
    
    stats = email_service.get_email_stats()
    recent_emails = email_service.get_recent_emails()
    
    return render_template(
        "admin/email-monitor.html",
        stats=stats,
        recent_emails=recent_emails
    )

@bp.route("/monitor/trigger", methods=["POST"])
@admin_required
def trigger_emails():
    """Manually trigger email processing."""
    success, message = scheduler.trigger_email_processing()
    return jsonify({
        "success": success,
        "message": message
    }), 200 if success else 500 