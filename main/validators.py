
from django.core.exceptions import ValidationError

def validate_resume(file):
    if file.size > 2 * 1024 * 1024:
        raise ValidationError("Resume file size must be <= 2MB")
    if not file.name.lower().endswith(('.pdf', '.doc', '.docx')):
        raise ValidationError("Only PDF/DOC/DOCX files allowed")
