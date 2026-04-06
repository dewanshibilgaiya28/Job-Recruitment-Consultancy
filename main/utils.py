def get_user_role(user):
    if user.is_staff:
        return "ADMIN"

    if hasattr(user, "stakeholder"):
        return user.stakeholder.role  # OWNER, RECRUITER, DEV_QA, ADMIN

    if hasattr(user, "client"):
        return "CLIENT"

    if hasattr(user, "candidate"):
        return "CANDIDATE"

    return "UNKNOWN"
