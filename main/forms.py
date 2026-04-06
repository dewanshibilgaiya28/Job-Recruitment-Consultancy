
"""
Enhanced forms with client-side and server-side validation
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Candidate, Client, Job, Application, Interview, ClientFeedback
from .validators import validate_resume
import re


class BaseFormMixin:
    """Mixin for common form methods"""
    
    def clean_data(self):
        """Sanitize all string inputs"""
        cleaned_data = super().clean()
        for field, value in cleaned_data.items():
            if isinstance(value, str):
                # Basic HTML escaping happens automatically in Django
                cleaned_data[field] = value.strip()
        return cleaned_data


class ApplyJobForm(forms.Form):
    """Resume upload required when applying for a job."""
    resume = forms.FileField(
        label="Resume (PDF, DOC, DOCX)",
        help_text="Upload your resume. Max 2MB. Required to apply.",
        widget=forms.FileInput(attrs={"accept": ".pdf,.doc,.docx", "class": "form-control"})
    )

    def clean_resume(self):
        resume = self.cleaned_data.get("resume")
        if not resume:
            raise forms.ValidationError("Resume is required to apply for this job.")
        try:
            validate_resume(resume)
        except ValidationError:
            raise
        return resume


class CandidateSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']


class CandidateProfileForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['phone', 'location', 'resume', 'skills', 'experience', 'profile_picture']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resume'].required = False
        self.fields['resume'].help_text = "Optional. Leave blank to keep current resume. PDF, DOC, DOCX, max 2MB."
        # profile_picture is optional
        self.fields['profile_picture'].required = False
        # Allow profile edits that only change account fields (first/last/email)
        self.fields['phone'].required = False
        self.fields['skills'].required = False
        self.fields['experience'].required = False

    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        if resume:
            is_existing_saved_file = bool(getattr(resume, "_committed", False))
            if not is_existing_saved_file:
                try:
                    validate_resume(resume)
                except ValidationError:
                    raise
            return resume

        if self.instance and self.instance.pk and self.instance.resume:
            return self.instance.resume

        raise ValidationError("Resume is required.")

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if phone:
            return phone
        if self.instance and self.instance.pk and self.instance.phone:
            return self.instance.phone
        raise ValidationError('Phone is required.')

    def clean_skills(self):
        skills = (self.cleaned_data.get('skills') or '').strip()
        if skills:
            return skills
        if self.instance and self.instance.pk and self.instance.skills:
            return self.instance.skills
        raise ValidationError('Skills are required.')

    def clean_experience(self):
        experience = self.cleaned_data.get('experience')
        if experience is not None:
            if experience < 0:
                raise ValidationError('Experience must be a non-negative number.')
            return experience
        if self.instance and self.instance.pk and self.instance.experience is not None:
            return self.instance.experience
        raise ValidationError('Experience is required.')


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean_username(self):
        return (self.cleaned_data.get('username') or '').strip()

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if not username or not password:
            return cleaned_data

        if not User.objects.filter(username=username).exists():
            self.add_error('username', 'Username not found.')
            return cleaned_data

        user = authenticate(self.request, username=username, password=password)
        if user is None:
            self.add_error('password', 'Incorrect password.')
            return cleaned_data

        if not user.is_active:
            raise ValidationError('This account is disabled.')

        self.user_cache = user
        return cleaned_data

    def get_user(self):
        return self.user_cache


class CandidateRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    skills = forms.CharField(widget=forms.Textarea)
    experience = forms.IntegerField(min_value=0, max_value=70)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    agree_terms = forms.BooleanField(required=True)

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        try:
            User._meta.get_field('username').run_validators(username)
        except ValidationError as exc:
            raise ValidationError(exc.messages)
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Username is already taken.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Email is already registered.')
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        compact = re.sub(r'[\s\-()]+', '', phone)
        if compact.startswith('+'):
            compact = compact[1:]
        if not compact.isdigit() or not (10 <= len(compact) <= 15):
            raise ValidationError('Enter a valid phone number (10-15 digits).')
        return phone

    def clean_skills(self):
        skills = (self.cleaned_data.get('skills') or '').strip()
        if len(skills) < 2:
            raise ValidationError('Please enter at least one skill.')
        return skills

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Passwords do not match.')

        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
        )
        Candidate.objects.create(
            user=user,
            phone=self.cleaned_data['phone'],
            skills=self.cleaned_data['skills'],
            experience=self.cleaned_data['experience'],
            resume='',
        )
        return user


class ClientRegistrationForm(forms.Form):
    INDUSTRY_CHOICES = [
        ('', 'Select Industry'),
        ('tech', 'Technology'),
        ('finance', 'Finance'),
        ('healthcare', 'Healthcare'),
        ('retail', 'Retail'),
        ('other', 'Other'),
    ]

    username = forms.CharField(max_length=150)
    company_name = forms.CharField(max_length=255)
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    industry = forms.ChoiceField(choices=INDUSTRY_CHOICES)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    agree_terms = forms.BooleanField(required=True)

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        try:
            User._meta.get_field('username').run_validators(username)
        except ValidationError as exc:
            raise ValidationError(exc.messages)
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Username is already taken.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Email is already registered.')
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        compact = re.sub(r'[\s\-()]+', '', phone)
        if compact.startswith('+'):
            compact = compact[1:]
        if not compact.isdigit() or not (10 <= len(compact) <= 15):
            raise ValidationError('Enter a valid phone number (10-15 digits).')
        return phone

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Passwords do not match.')

        return cleaned_data

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
        )
        Client.objects.create(
            user=user,
            company_name=self.cleaned_data['company_name'],
            contact_number=self.cleaned_data['phone'],
        )
        return user


class EnhancedCandidateSignupForm(BaseFormMixin, forms.ModelForm):
    """Signup form for candidates with enhanced validation"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='At least 12 characters with uppercase, lowercase, numbers, and symbols.'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Confirm Password'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        help_text='Use a valid email address'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def clean_username(self):
        """Validate username format and uniqueness"""
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('Username is required')
        
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters')
        if len(username) > 30:
            raise ValidationError('Username must be less than 30 characters')
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError('Username can only contain letters, numbers, and underscores')
        
        if User.objects.filter(username=username).exists():
            raise ValidationError('Username already exists')
        
        return username
    
    def clean_email(self):
        """Validate email format and uniqueness"""
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError('Email is required')
        
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email already registered')
        
        return email
    
    def clean_password(self):
        """Validate password strength"""
        password = self.cleaned_data.get('password')
        if not password:
            raise ValidationError('Password is required')
        
        if len(password) < 12:
            raise ValidationError('Password must be at least 12 characters')
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            raise ValidationError(
                'Password must contain uppercase, lowercase, and numbers'
            )
        
        return password
    
    def clean(self):
        """Validate password confirmation"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm:
            if password != password_confirm:
                raise ValidationError('Passwords do not match')
        
        return cleaned_data


class EnhancedClientSignupForm(BaseFormMixin, forms.ModelForm):
    """Signup form for clients (employers) with enhanced validation"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='At least 12 characters with uppercase, lowercase, numbers, and symbols.'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Confirm Password'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        help_text='Use a valid email address'
    )
    company_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Your company name (max 255 characters)'
    )
    contact_number = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Your contact number'
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    
    def clean_username(self):
        """Validate username"""
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('Username is required')
        
        if len(username) < 3:
            raise ValidationError('Username must be at least 3 characters')
        
        if User.objects.filter(username=username).exists():
            raise ValidationError('Username already exists')
        
        return username
    
    def clean_email(self):
        """Validate email format and uniqueness"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email already registered')
        
        return email
    
    def clean_company_name(self):
        """Validate company name"""
        company_name = self.cleaned_data.get('company_name')
        if not company_name:
            raise ValidationError('Company name is required')
        
        if len(company_name) < 2:
            raise ValidationError('Company name must be at least 2 characters')
        
        return company_name
    
    def clean_contact_number(self):
        """Validate phone number"""
        contact_number = self.cleaned_data.get('contact_number')
        if not contact_number:
            raise ValidationError('Contact number is required')
        
        return contact_number
    
    def clean_password(self):
        """Validate password strength"""
        password = self.cleaned_data.get('password')
        if len(password) < 12:
            raise ValidationError('Password must be at least 12 characters')
        
        if not (any(c.isupper() for c in password) and 
                any(c.islower() for c in password) and
                any(c.isdigit() for c in password)):
            raise ValidationError('Password must contain uppercase, lowercase, and numbers')
        
        return password
    
    def clean(self):
        """Validate password confirmation"""
        cleaned_data = super().clean()
        if cleaned_data.get('password') != cleaned_data.get('password_confirm'):
            raise ValidationError('Passwords do not match')
        
        return cleaned_data


class EnhancedCandidateProfileForm(BaseFormMixin, forms.ModelForm):
    """Enhanced profile form for candidates"""
    
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Valid phone number (10+ digits)'
    )
    skills = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        help_text='Enter your skills (comma-separated, max 500 characters)'
    )
    experience = forms.IntegerField(
        min_value=0,
        max_value=70,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text='Years of experience (0-70)'
    )
    resume = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
        help_text='Upload resume (PDF/DOC/DOCX, max 2MB)'
    )
    
    class Meta:
        model = Candidate
        fields = ['phone', 'skills', 'experience', 'resume']
    
    def clean_phone(self):
        """Validate phone number"""
        phone = self.cleaned_data.get('phone')
        if not phone:
            raise ValidationError('Phone number is required')
        
        return phone
    
    def clean_skills(self):
        """Validate skills input"""
        skills = self.cleaned_data.get('skills')
        if not skills:
            raise ValidationError('Skills are required')
        
        if len(skills) > 500:
            raise ValidationError('Skills description must be less than 500 characters')
        
        if len(skills) < 5:
            raise ValidationError('Please provide more details about your skills')
        
        return skills.strip()
    
    def clean_experience(self):
        """Validate experience"""
        experience = self.cleaned_data.get('experience')
        if experience is None:
            raise ValidationError('Years of experience is required')
        
        if experience < 0 or experience > 70:
            raise ValidationError('Experience must be between 0 and 70 years')
        
        return experience
    
    def clean_resume(self):
        """Validate resume file"""
        resume = self.cleaned_data.get('resume')
        if not resume:
            return resume
        
        try:
            validate_resume(resume)
        except ValidationError:
            raise
        
        return resume


class EnhancedJobPostForm(BaseFormMixin, forms.ModelForm):
    """Enhanced form for posting jobs"""
    
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Job title (max 255 characters)'
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
        help_text='Detailed job description (max 2000 characters)'
    )
    location = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Job location'
    )
    salary = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Salary range (e.g., $50,000 - $70,000)'
    )
    job_type = forms.ChoiceField(
        choices=[('Full-time', 'Full-time'), ('Part-time', 'Part-time'), ('Contract', 'Contract')],
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    
    class Meta:
        model = Job
        fields = ['title', 'description', 'location', 'salary', 'job_type']
    
    def clean_title(self):
        """Validate job title"""
        title = self.cleaned_data.get('title')
        if not title:
            raise ValidationError('Job title is required')
        
        if len(title) < 5:
            raise ValidationError('Job title must be at least 5 characters')
        
        if not re.match(r'^[a-zA-Z0-9\s\-\(\)&,]+$', title):
            raise ValidationError('Job title contains invalid characters')
        
        return title.strip()
    
    def clean_description(self):
        """Validate job description"""
        description = self.cleaned_data.get('description')
        if not description:
            raise ValidationError('Job description is required')
        
        if len(description) < 50:
            raise ValidationError('Job description must be at least 50 characters')
        
        if len(description) > 2000:
            raise ValidationError('Job description must be less than 2000 characters')
        
        return description.strip()
    
    def clean_location(self):
        """Validate location"""
        location = self.cleaned_data.get('location')
        if not location:
            raise ValidationError('Location is required')
        
        if len(location) < 3:
            raise ValidationError('Location must be at least 3 characters')
        
        return location.strip()


class EnhancedApplicationForm(BaseFormMixin, forms.ModelForm):
    """Enhanced form for job applications"""
    
    resume = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.doc,.docx'}),
        help_text='Upload your resume (PDF, DOC, DOCX, max 2MB)'
    )
    
    class Meta:
        model = Application
        fields = []
    
    def clean_resume(self):
        """Validate resume"""
        resume = self.cleaned_data.get('resume')
        if not resume:
            raise ValidationError('Resume is required to apply')
        
        try:
            validate_resume(resume)
        except ValidationError:
            raise
        
        return resume


class EnhancedInterviewScheduleForm(BaseFormMixin, forms.ModelForm):
    """Enhanced form for scheduling interviews"""
    
    interview_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        help_text='Select interview date and time'
    )
    mode = forms.ChoiceField(
        choices=[('Online', 'Online'), ('Offline', 'Offline'), ('Phone', 'Phone')],
        widget=forms.RadioSelect(),
        help_text='Select interview mode'
    )
    
    class Meta:
        model = Interview
        fields = ['interview_date', 'mode']
    
    def clean_interview_date(self):
        """Validate interview date"""
        from django.utils import timezone
        from datetime import timedelta
        
        interview_date = self.cleaned_data.get('interview_date')
        
        if not interview_date:
            raise ValidationError('Interview date is required')
        
        if interview_date < timezone.now():
            raise ValidationError('Interview date must be in the future')
        
        future_limit = timezone.now() + timedelta(days=90)
        if interview_date > future_limit:
            raise ValidationError('Interview date must be within 90 days')
        
        return interview_date


class EnhancedFeedbackForm(BaseFormMixin, forms.ModelForm):
    """Enhanced form for client feedback"""
    
    feedback = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        help_text='Provide your feedback (max 1000 characters)'
    )
    
    class Meta:
        model = ClientFeedback
        fields = ['feedback']
    
    def clean_feedback(self):
        """Validate feedback"""
        feedback = self.cleaned_data.get('feedback')
        if not feedback:
            raise ValidationError('Feedback is required')
        
        if len(feedback) < 10:
            raise ValidationError('Feedback must be at least 10 characters')
        
        if len(feedback) > 1000:
            raise ValidationError('Feedback must be less than 1000 characters')
        
        return feedback.strip()
