from django.db import models
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta

# Client (Employer)
class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255, db_index=True)
    contact_number = models.CharField(max_length=20)
    company_logo = models.ImageField(upload_to='company_logos/%Y/%m/', null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/%Y/%m/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.company_name} ({self.user.username})"

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['company_name']
        indexes = [
            models.Index(fields=['company_name']),
            models.Index(fields=['-created_at']),
        ]


# Candidate
class Candidate(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    location = models.CharField(max_length=255, null=True, blank=True)
    resume = models.FileField(upload_to='resumes/')
    # profile picture for candidate (optional)
    profile_picture = models.ImageField(upload_to='profile_pictures/%Y/%m/', null=True, blank=True)
    skills = models.TextField()
    experience = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

    class Meta:
        verbose_name = "Candidate"
        verbose_name_plural = "Candidates"
        ordering = ['user__username']
        indexes = [
            models.Index(fields=['-created_at']),
        ]


# Job
class Job(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='jobs')
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    location = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    job_type = models.CharField(max_length=50, default="Full-time", null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    salary = models.CharField(max_length=100, default="", blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        client_name = self.client.company_name if self.client else "No client"
        return f"{self.title} at {client_name}"

    def clean(self):
        if not self.client:
            raise ValidationError("Job must have a client")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Job"
        verbose_name_plural = "Jobs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['location']),
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['client', 'is_active']),
        ]


# Applications
class Application(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    resume = models.FileField(upload_to='application_resumes/%Y/%m/', null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    STATUS_CHOICES = [
        ("APPLIED", "Applied"),
        ("SHORTLISTED", "Shortlisted"),
        ("INTERVIEWED", "Interviewed"),
        ("SELECTED", "Selected"),
        ("REJECTED", "Rejected"),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='APPLIED', db_index=True)

    def __str__(self):
        return f"{self.candidate} applied for {self.job.title} [{self.status}]"

    class Meta:
        verbose_name = "Application"
        verbose_name_plural = "Applications"
        ordering = ['-applied_at']
        unique_together = ('job', 'candidate')
        indexes = [
            models.Index(fields=['status', '-applied_at']),
            models.Index(fields=['candidate']),
            models.Index(fields=['job', 'status']),
        ]


# Stakeholder
class Stakeholder(models.Model):
    ROLE_CHOICES = [
        ('OWNER', 'Recruitment Consultancy Owner'),
        ('RECRUITER', 'Recruiter / HR Consultant'),
        ('CLIENT', 'Client Company'),
        ('CANDIDATE', 'Job Seeker'),
        ('ADMIN', 'System Administrator'),
        ('DEV_QA', 'Development & QA Team'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='stakeholder')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/%Y/%m/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    skills = models.TextField(blank=True, default='')
    experience = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    class Meta:
        verbose_name = "Stakeholder"
        verbose_name_plural = "Stakeholders"
        ordering = ['role']
        indexes = [
            models.Index(fields=['role']),
        ]


# Interview
class Interview(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='interviews')
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='interviews')
    scheduled_by = models.ForeignKey(User, on_delete=models.CASCADE)
    interview_date = models.DateTimeField(null=True, blank=True, db_index=True)
    application = models.OneToOneField("Application", on_delete=models.CASCADE, null=True, blank=True)
    mode = models.CharField(max_length=50, default="Online")

    def __str__(self):
        return f"Interview: {self.candidate} for {self.job.title} on {self.interview_date}"

    class Meta:
        verbose_name = "Interview"
        verbose_name_plural = "Interviews"
        ordering = ['interview_date']
        indexes = [
            models.Index(fields=['interview_date']),
            models.Index(fields=['job', 'candidate']),
        ]


# ClientFeedback
class ClientFeedback(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    feedback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        job = getattr(self, 'job', None)
        client_name = getattr(job.client, 'company_name', 'Unknown Client') if job and getattr(job, 'client', None) else 'Unknown Client'
        candidate_name = getattr(self, 'candidate', 'Unknown Candidate')
        return f"Feedback by {client_name} for {candidate_name}"

    class Meta:
        verbose_name = "Client Feedback"
        verbose_name_plural = "Client Feedbacks"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]

# Feedback
class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    rating = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, null=True, blank=True)

    def __str__(self):
        return f"Feedback from {self.user.username}"

    class Meta:
        verbose_name = "Feedback"
        verbose_name_plural = "Feedbacks"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]


# ============================================================================
# ANALYTICS & AUDIT MODELS
# ============================================================================

class AuditLog(models.Model):
    """Track all security-sensitive operations"""
    
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VIEW', 'View'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('INTERVIEW', 'Interview'),
        ('OTHER', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    resource_type = models.CharField(max_length=100, db_index=True)
    resource_id = models.IntegerField(null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['resource_type', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.resource_type} ({self.timestamp})"
