from datetime import datetime, timedelta
import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail
from django.db.models import Count, Q, F
from django.contrib import messages
from .models import Candidate, Client, Job, Application, Stakeholder, Interview, Feedback, ClientFeedback
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .utils import get_user_role
from .decorators import role_required, custom_role_required
from .forms import (
    ApplyJobForm,
    EnhancedFeedbackForm,
    CandidateProfileForm,
    CandidateRegistrationForm,
    ClientRegistrationForm,
    LoginForm,
)
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO


def _redirect_forbidden(request, message="You do not have access to this page."):
    
    
    
    
    messages.error(request, message)
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


DASHBOARD_TIME_FILTER_OPTIONS = [
    ("all", "All Time"),
    ("today", "Today"),
    ("week", "Last 7 Days"),
    ("month", "Last 30 Days"),
    ("quarter", "Last 90 Days"),
    ("year", "Last 365 Days"),
]


def _get_dashboard_time_window(raw_value):
    now = timezone.now()
    valid_values = {value for value, _ in DASHBOARD_TIME_FILTER_OPTIONS}
    normalized = (raw_value or "all").strip().lower()
    if normalized not in valid_values:
        normalized = "all"

    start_dt = None
    end_dt = None

    if normalized == "today":
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif normalized == "week":
        start_dt = now - timedelta(days=7)
        end_dt = now + timedelta(days=7)
    elif normalized == "month":
        start_dt = now - timedelta(days=30)
        end_dt = now + timedelta(days=30)
    elif normalized == "quarter":
        start_dt = now - timedelta(days=90)
        end_dt = now + timedelta(days=90)
    elif normalized == "year":
        start_dt = now - timedelta(days=365)
        end_dt = now + timedelta(days=365)

    return normalized, start_dt, end_dt, now

# ----------------------------
# 0. Dashboard
# ----------------------------
@login_required
def dashboard(request):
    role = get_user_role(request.user)
    if role in ["OWNER", "RECRUITER", "DEV_QA"]:
        return redirect("recruiter_dashboard")
    elif role == "CLIENT":
        return redirect("client_dashboard")
    elif role == "CANDIDATE":
        return redirect("candidate_dashboard")
    else:
        return redirect("job_list")


def home(request):
    jobs = Job.objects.select_related("client").order_by("-id")[:6]
    return render(request, "main/home.html", {"jobs": jobs})


def favicon(request):
    svg = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>
    <defs><style>.a{fill:#0a3357}.b{fill:#f6b01c}.c{fill:#ffffff}</style></defs>
    <rect class='a' width='64' height='64' rx='12'/>
    <circle class='b' cx='32' cy='32' r='18'/>
    <text x='32' y='38' text-anchor='middle' font-size='20' fill='#111827' font-family='Arial, sans-serif' font-weight='700'>Q</text>
    </svg>"""
    return HttpResponse(svg, content_type="image/svg+xml")


INFO_PAGES = {
    "company_profile": {
        "title": "Company Profile",
        "subtitle": "A globally trusted leader in staffing solutions",
        "description": "Quess Corp Limited delivers workforce solutions across industries with scale, speed, and domain expertise.",
        "bullets": [
            "Integrated staffing, outsourcing, and HR services",
            "Future-ready digital platforms for workforce management",
            "Presence across multiple geographies and industries",
        ],
    },
    "leadership": {
        "title": "Leadership",
        "subtitle": "Experienced leaders building trusted partnerships",
        "description": "Our leadership team blends industry expertise with a people-first mindset to guide transformation.",
        "bullets": [
            "Strategic focus on talent and technology",
            "Commitment to compliance and governance",
            "Customer-centric delivery across the lifecycle",
        ],
    },
    "csr": {
        "title": "CSR",
        "subtitle": "Creating impact beyond business",
        "description": "We invest in education, employability, and community initiatives to drive sustainable change.",
        "bullets": [
            "Skill development and employability programs",
            "Community partnerships and volunteer initiatives",
            "Inclusive growth and wellbeing focus",
        ],
    },
    "sustainability": {
        "title": "Sustainability",
        "subtitle": "Responsible growth for a resilient future",
        "description": "We embed sustainability into how we serve clients, candidates, and communities.",
        "bullets": [
            "Ethical and compliant workforce practices",
            "Responsible sourcing and operational efficiencies",
            "Long-term stakeholder value creation",
        ],
    },
    "services_general_staffing": {
        "title": "General Staffing",
        "subtitle": "Flexible staffing built for scale",
        "description": "Deploy skilled associates quickly and reliably across geographies and business cycles.",
        "bullets": [
            "Large talent pools and rapid mobilization",
            "End-to-end compliance management",
            "Operational visibility and governance",
        ],
    },
    "services_professional_staffing": {
        "title": "Professional Staffing",
        "subtitle": "Specialist talent for critical roles",
        "description": "Source niche and specialized talent with domain-aligned recruiters and screening.",
        "bullets": [
            "Role-specific hiring frameworks",
            "Industry-focused sourcing",
            "Quality assurance and retention focus",
        ],
    },
    "services_digital_platform": {
        "title": "Digital Platform",
        "subtitle": "Technology that orchestrates talent",
        "description": "Digital tools that streamline hiring, onboarding, payroll, and lifecycle management.",
        "bullets": [
            "Applicant tracking and onboarding automation",
            "Payroll and compliance workflows",
            "Real-time analytics and reporting",
        ],
    },
    "services_gcc": {
        "title": "Global Capability Centers",
        "subtitle": "Build and scale GCCs with confidence",
        "description": "Launch, grow, and optimize GCCs with proven workforce and operational support.",
        "bullets": [
            "End-to-end GCC setup",
            "Talent acquisition and retention strategy",
            "Operational governance and cost optimization",
        ],
    },
    "blogs": {
        "title": "Blogs",
        "subtitle": "Insights on staffing, talent, and technology",
        "description": "Explore articles that help organizations hire smarter and operate faster.",
        "bullets": [
            "Hiring trends and workforce insights",
            "Operational best practices",
            "Technology and automation updates",
        ],
    },
    "case_studies": {
        "title": "Case Studies",
        "subtitle": "Customer outcomes and success stories",
        "description": "See how we deliver measurable impact across industries and business objectives.",
        "bullets": [
            "Large-scale hiring transformations",
            "Productivity and engagement improvements",
            "Digital platform rollouts",
        ],
    },
    "knowledge_base": {
        "title": "Knowledge Base",
        "subtitle": "Resources to guide your hiring strategy",
        "description": "Access guides, playbooks, and tools that simplify workforce decisions.",
        "bullets": [
            "Hiring frameworks",
            "Compliance and governance checklists",
            "Process and operational guides",
        ],
    },
    "investors": {
        "title": "Investors",
        "subtitle": "Building sustainable, long-term value",
        "description": "Financial highlights, governance, and strategic updates for investors.",
        "bullets": [
            "Investor communications and announcements",
            "Corporate governance and disclosures",
            "Performance highlights",
        ],
    },
    "media": {
        "title": "Media",
        "subtitle": "Press releases and brand updates",
        "description": "Latest news, announcements, and media coverage from Quess Corp.",
        "bullets": [
            "Press releases",
            "Media coverage",
            "Brand assets and announcements",
        ],
    },
    "contact_us": {
        "title": "Contact Us",
        "subtitle": "Let’s build your workforce together",
        "description": "Reach out to our teams for partnerships, services, and career opportunities.",
        "bullets": [
            "Email: hello@quesscorp.com",
            "Phone: +1 (415) 555-0183",
            "Office hours: Mon–Fri, 9am–6pm",
        ],
    },
}


def info_page(request, slug):
    page = INFO_PAGES.get(slug)
    if not page:
        raise Http404("Page not found")
    return render(request, "main/info_page.html", {"page": page})
    


# 1. Candidate Registration
def candidate_register(request):
    if request.method == 'POST':
        form = CandidateRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful. Please login.")
            return redirect('login')
    else:
        form = CandidateRegistrationForm()

    return render(request, 'main/candidate_register.html', {'form': form})





# 2. Client Registration
def client_register(request):
    if request.method == 'POST':
        form = ClientRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Employer registration successful. Please login.")
            return redirect('login')
    else:
        form = ClientRegistrationForm()

    return render(request, 'main/client_register.html', {'form': form})





@login_required
@role_required('client')
def job_post(request):
    if request.method == 'POST':
        # 🔹 Get the logged-in client's object
        try:
            client = request.user.client
        except Client.DoesNotExist:
            return HttpResponse("Client profile not found.", status=400)

        # 🔹 Get required fields
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not title or not description:
            messages.error(request, "Title and description are required.")
            return redirect("job_post")

        # 🔹 Create Job with provided fields
        Job.objects.create(
            client=client,
            title=title,
            description=description,
            location=request.POST.get('location', 'Not Specified'),
            job_type=request.POST.get('job_type', 'Full-time'),
            salary=request.POST.get('salary', '')
        )
        return redirect('job_list')  # redirect to job list page

    # GET request
    return render(request, 'main/job_post.html')


# 4. Job List
def job_list(request):
    jobs = Job.objects.select_related("client").all()
    return render(request, 'main/job_list.html', {'jobs': jobs})








# 5. Apply Job (resume required)
@login_required
@role_required('candidate')
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    candidate = Candidate.objects.get(user=request.user)

    # Check if already applied
    if Application.objects.filter(job=job, candidate=candidate).exists():
        from django.contrib import messages
        messages.warning(request, "You have already applied for this job.")
        return redirect("job_detail", job_id=job_id)

    if request.method == "POST":
        form = ApplyJobForm(request.POST, request.FILES)
        if form.is_valid():
            resume_file = form.cleaned_data["resume"]
            Application.objects.create(
                job=job,
                candidate=candidate,
                resume=resume_file
            )
            from django.contrib import messages
            messages.success(request, "Application submitted successfully.")
            return redirect("candidate_dashboard")
        messages.error(request, "Please correct the errors and try again.")
        return redirect("apply_job", job_id=job_id)
    else:
        form = ApplyJobForm()

    return render(request, "main/apply_job.html", {"job": job, "form": form})






# Login/logout
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            role = get_user_role(user)

            if role == "ADMIN":
                return redirect("/admin/")

            if role in ["OWNER", "RECRUITER", "DEV_QA"]:
                return redirect("recruiter_dashboard")

            if role == "CLIENT":
                return redirect("client_dashboard")

            if role == "CANDIDATE":
                return redirect("candidate_dashboard")

            return redirect("dashboard")
    else:
        form = LoginForm()

    return render(request, "main/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


# ----------------------------
# Profile (all user types)
# ----------------------------
@login_required
def profile_view(request):
    """Show profile for current user (candidate, client, or recruiter/stakeholder).

    Use primary role (from get_user_role) so a user that accidentally has multiple
    role-related objects sees the correct profile section only.
    """
    user = request.user
    role = get_user_role(user)

    context = {"profile_user": user, "role": role}

    # Prefer primary role determined by get_user_role()
    if role == "CANDIDATE" and hasattr(user, "candidate"):
        context["candidate"] = user.candidate
    elif role == "CLIENT" and hasattr(user, "client"):
        context["client"] = user.client
    elif role in ("OWNER", "RECRUITER", "DEV_QA", "ADMIN") and hasattr(user, "stakeholder"):
        context["stakeholder"] = user.stakeholder
    else:
        # Fallback: include only one sensible relation to avoid showing multiple blocks
        if hasattr(user, "client"):
            context["client"] = user.client
        elif hasattr(user, "candidate"):
            context["candidate"] = user.candidate
        elif hasattr(user, "stakeholder"):
            context["stakeholder"] = user.stakeholder

    return render(request, "main/profile.html", context)


@login_required
def profile_edit(request):
    """Edit profile based on the user's primary role.

    Uses get_user_role() to avoid showing candidate fields to client users who
    may have a stray Candidate object in the database.
    """
    user = request.user
    role = get_user_role(user)

    def _build_context(candidate_form=None):
        context = {"profile_user": user, "role": role}
        if role == "CANDIDATE" and hasattr(user, "candidate"):
            context["form"] = candidate_form if candidate_form is not None else CandidateProfileForm(instance=user.candidate)
        elif role == "CLIENT" and hasattr(user, "client"):
            context["client"] = user.client
        elif role in ("OWNER", "RECRUITER", "DEV_QA") and hasattr(user, "stakeholder"):
            context["stakeholder"] = user.stakeholder
        return context

    # ---- POST handling based on primary role ----
    if request.method == "POST":
        requested_username = request.POST.get("username", "").strip()
        username_errors = []

        if not requested_username:
            username_errors.append("Username is required.")
        else:
            try:
                User._meta.get_field("username").run_validators(requested_username)
            except DjangoValidationError as exc:
                username_errors.extend(exc.messages)

            if User.objects.exclude(pk=user.pk).filter(username__iexact=requested_username).exists():
                username_errors.append("Username is already taken.")

        if username_errors:
            for error in username_errors:
                messages.error(request, error)

            candidate_form = None
            if role == "CANDIDATE" and hasattr(user, "candidate"):
                candidate_form = CandidateProfileForm(request.POST, request.FILES, instance=user.candidate)

            return render(request, "main/profile_edit.html", _build_context(candidate_form))

        # Candidate update
        if role == "CANDIDATE" and hasattr(user, "candidate"):
            form = CandidateProfileForm(request.POST, request.FILES, instance=user.candidate)
            if form.is_valid():
                form.save()
                user.username = requested_username
                user.first_name = request.POST.get("first_name", user.first_name)
                user.last_name = request.POST.get("last_name", user.last_name)
                user.email = request.POST.get("email", user.email)
                user.save()
                messages.success(request, "Profile updated successfully.")
                return redirect("profile")
            else:
                for field_name, error_list in form.errors.items():
                    if field_name == "__all__":
                        label = "Form"
                    else:
                        label = form.fields[field_name].label or field_name.replace("_", " ").title()
                    for error in error_list:
                        messages.error(request, f"{label}: {error}")

        # Client update
        elif role == "CLIENT" and hasattr(user, "client"):
            c = user.client
            c.company_name = request.POST.get("company_name", c.company_name)
            c.contact_number = request.POST.get("contact_number", c.contact_number)
            
            # Handle company logo upload
            if request.FILES.get('company_logo'):
                c.company_logo = request.FILES.get('company_logo')
            
            # Handle profile picture upload
            if request.FILES.get('profile_picture'):
                c.profile_picture = request.FILES.get('profile_picture')
            
            c.save()
            user.username = requested_username
            user.first_name = request.POST.get("first_name", user.first_name)
            user.last_name = request.POST.get("last_name", user.last_name)
            user.email = request.POST.get("email", user.email)
            user.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")

        # Stakeholder / recruiter / owner
        elif role in ("OWNER", "RECRUITER", "DEV_QA") and hasattr(user, "stakeholder"):
            s = user.stakeholder

            s.phone = request.POST.get("phone", s.phone).strip()
            s.location = request.POST.get("location", s.location).strip()
            s.skills = request.POST.get("skills", s.skills).strip()

            experience_raw = request.POST.get("experience", "").strip()
            if experience_raw == "":
                s.experience = None
            else:
                try:
                    parsed_experience = int(experience_raw)
                    if parsed_experience < 0:
                        raise ValueError
                    s.experience = parsed_experience
                except ValueError:
                    messages.error(request, "Experience must be a non-negative number.")
                    return render(request, "main/profile_edit.html", _build_context())

            if request.FILES.get("profile_picture"):
                s.profile_picture = request.FILES.get("profile_picture")
            s.save()

            user.username = requested_username
            user.first_name = request.POST.get("first_name", user.first_name)
            user.last_name = request.POST.get("last_name", user.last_name)
            user.email = request.POST.get("email", user.email)
            user.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")

        else:
            messages.error(request, "Profile update not supported for your account.")

    return render(request, "main/profile_edit.html", _build_context())


@login_required
def resume_tips(request):
    """Short guidance page: resume writing tips."""
    return render(request, "main/resources/resume_tips.html")


@login_required
def interview_prep(request):
    """Short guidance page: interview preparation."""
    return render(request, "main/resources/interview_prep.html")


@login_required
def job_search_guide(request):
    """Short guidance page: job search strategy and tips."""
    return render(request, "main/resources/job_search_guide.html")


def job_search(request):
    """Search jobs by title, description, company name or location. Returns only active jobs.

    - empty query -> all active jobs
    - non-empty -> case-insensitive search across multiple fields
    """
    q = request.GET.get("q", "").strip()

    if not q:
        jobs = Job.objects.filter(is_active=True).select_related("client").order_by("-created_at")
    else:
        query = (
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(client__company_name__icontains=q) |
            Q(location__icontains=q)
        )
        jobs = (
            Job.objects.filter(query, is_active=True)
            .select_related("client")
            .order_by("-created_at")
            .distinct()
        )

    return render(request, "main/job_list.html", {"jobs": jobs})


def job_filter(request):
    """Filter jobs by location and/or keyword (title/description). Only active jobs are returned."""
    location = request.GET.get("location", "").strip()
    skill = request.GET.get("skill", "").strip()

    qs = Job.objects.filter(is_active=True)
    if location:
        qs = qs.filter(location__iexact=location)
    if skill:
        qs = qs.filter(Q(title__icontains=skill) | Q(description__icontains=skill))

    return render(request, "main/job_list.html", {"jobs": qs})



@login_required
def my_applications(request):

    if not hasattr(request.user, "candidate"):
        return _redirect_forbidden(request, "Only candidates can view applications.")

    applications = Application.objects.filter(candidate=request.user.candidate)

    return render(request, "main/application_status.html", {
        "applications": applications
    })

 
# @login_required
# def my_applications(request):
#     apps = Application.objects.filter(candidate__user=request.user)
#     return render(request, "main/application_status.html", {"applications": apps})


@login_required
def schedule_interview(request, application_id):

    # Only recruiters / stakeholders allowed
    if not hasattr(request.user, "stakeholder"):
        return _redirect_forbidden(request, "Only recruiters are allowed.")

    application = get_object_or_404(Application, id=application_id)

    # Try to get existing interview
    interview, created = Interview.objects.get_or_create(
        application=application,
        defaults={
            'job': application.job,
            'candidate': application.candidate,
            'scheduled_by': request.user,
        }
    )

    if request.method == "POST":
        # Accept either `date`/`time` (canonical) or legacy `interview_date`/`interview_time`
        date_str = request.POST.get("date") or request.POST.get("interview_date")   # YYYY-MM-DD
        time_str = request.POST.get("time") or request.POST.get("interview_time")   # HH:MM

        if not date_str or not time_str:
            messages.error(request, "Date and time are required.")
            return redirect("schedule_interview", application_id=application_id)

        # Combine date + time
        interview_datetime = datetime.strptime(
            f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
        )

        # Update interview datetime
        interview.interview_date = interview_datetime
        interview.scheduled_by = request.user
        interview.save()

        # Send email
        send_mail(
            subject="Interview Scheduled",
            message=f"""
Hello {application.candidate.user.username},

Your interview has been scheduled successfully.

Job Title : {application.job.title}
Company   : {application.job.client.company_name}
Date & Time : {interview_datetime.strftime('%d %b %Y, %I:%M %p')}

Please be available on time.

Regards,
Recruitment Team
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[application.candidate.user.email],
            fail_silently=False,
        )

        return redirect("recruiter_applications")

    return render(request, "main/schedule_interview.html", {
        "application": application,
        "interview": interview
    })






@login_required
def update_status(request, app_id, new_status):
    app = get_object_or_404(Application, id=app_id)
    role = get_user_role(request.user)

    can_update = False
    if role in ["OWNER", "DEV_QA", "ADMIN"]:
        can_update = True
    if role == "RECRUITER" and new_status == "APPLIED":
        can_update = True
    if hasattr(request.user, "client") and app.job.client_id == request.user.client.id:
        can_update = True

    if not can_update:
        return _redirect_forbidden(request, "You do not have permission to update application status.")

    app.status = new_status
    app.save(update_fields=["status"])
    return redirect("application_detail", application_id=app.id)






def active_jobs_report(request):
    jobs = Job.objects.filter(is_active=True)
    return render(request, "main/reports/active_jobs.html", {"jobs": jobs})







def candidate_pipeline_report(request):
    pipeline = {
        "applied": Application.objects.filter(status="APPLIED").count(),
        "shortlisted": Application.objects.filter(status="SHORTLISTED").count(),
        "interviewed": Application.objects.filter(status="INTERVIEWED").count(),
        "selected": Application.objects.filter(status="SELECTED").count(),
        "rejected": Application.objects.filter(status="REJECTED").count(),
    }
    return render(request, "main/reports/pipeline.html", {"pipeline": pipeline})








@login_required
@custom_role_required(['OWNER', 'RECRUITER', 'DEV_QA'])
def recruiter_performance_report(request):
    data = Stakeholder.objects.filter(role="RECRUITER").annotate(
        placements=Count(
            "user__interview__application",
            filter=Q(user__interview__application__status="SELECTED")
        )
    )
    return render(request, "main/reports/recruiter_performance.html", {"data": data})








def client_placement_report(request):
    data = Client.objects.annotate(
        placements=Count("jobs__applications", filter=Q(jobs__applications__status="SELECTED"), distinct=True)
    )
    return render(request, "main/reports/client_placements.html", {"data": data})






@login_required
def recruiter_only_view(request):
    if request.user.stakeholder.role != "RECRUITER":
        return _redirect_forbidden(request)


@login_required
def secure_view(request):
    if request.user.stakeholder.role != "ADMIN":
        return _redirect_forbidden(request)
    



def select_candidate(request, application_id):
    application = Application.objects.get(id=application_id)
    application.status = "SELECTED"
    application.save()


def submit_feedback(request):
    Feedback.objects.create(
        user=request.user,
        message=request.POST["message"],
        rating=request.POST["rating"]
    )



@login_required
def recruiter_dashboard(request):
    role = get_user_role(request.user)
    if role not in ["OWNER", "RECRUITER", "DEV_QA"]:
        return _redirect_forbidden(request)

    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "APPLIED").strip().upper()
    mode_filter = request.GET.get("mode", "").strip()
    time_filter = request.GET.get("time_filter", "all")
    pending_page_number = request.GET.get("pending_page", 1)
    interview_page_number = request.GET.get("interview_page", 1)

    time_filter, start_dt, end_dt, now = _get_dashboard_time_window(time_filter)

    valid_status_values = {code for code, _ in Application.STATUS_CHOICES}
    if status_filter not in valid_status_values and status_filter != "ALL":
        status_filter = "APPLIED"

    interview_mode_options = list(
        Interview.objects.exclude(mode__isnull=True)
        .exclude(mode__exact="")
        .order_by("mode")
        .values_list("mode", flat=True)
        .distinct()
    )
    
    applications_base_qs = Application.objects.all()
    if start_dt is not None:
        applications_base_qs = applications_base_qs.filter(applied_at__gte=start_dt)

    # Total applications across all jobs
    total_applications = applications_base_qs.count()

    # Shortlisted applications (status = SHORTLISTED)
    shortlisted_count = applications_base_qs.filter(status='SHORTLISTED').count()

    # Placements (applications with status = SELECTED)
    placements_count = applications_base_qs.filter(status='SELECTED').count()

    interviews_metric_qs = Interview.objects.filter(interview_date__gte=now)
    if end_dt is not None:
        interviews_metric_qs = interviews_metric_qs.filter(interview_date__lte=end_dt)
    interviews_count = interviews_metric_qs.count()

    pending_applications_qs = applications_base_qs.select_related('candidate', 'job', 'candidate__user')

    if status_filter != "ALL":
        pending_applications_qs = pending_applications_qs.filter(status=status_filter)

    upcoming_interviews_qs = Interview.objects.filter(
        interview_date__gte=now
    ).select_related('candidate', 'job', 'candidate__user')

    if end_dt is not None:
        upcoming_interviews_qs = upcoming_interviews_qs.filter(interview_date__lte=end_dt)

    if q:
        pending_applications_qs = pending_applications_qs.filter(
            Q(candidate__user__first_name__icontains=q) |
            Q(candidate__user__last_name__icontains=q) |
            Q(candidate__user__username__icontains=q) |
            Q(job__title__icontains=q) |
            Q(job__client__company_name__icontains=q)
        )

        upcoming_interviews_qs = upcoming_interviews_qs.filter(
            Q(candidate__user__first_name__icontains=q) |
            Q(candidate__user__last_name__icontains=q) |
            Q(candidate__user__username__icontains=q) |
            Q(job__title__icontains=q) |
            Q(job__client__company_name__icontains=q)
        )

    if mode_filter:
        upcoming_interviews_qs = upcoming_interviews_qs.filter(mode__iexact=mode_filter)

    pending_paginator = Paginator(pending_applications_qs.order_by('-applied_at'), 10)
    try:
        pending_page_obj = pending_paginator.page(pending_page_number)
    except PageNotAnInteger:
        pending_page_obj = pending_paginator.page(1)
    except EmptyPage:
        pending_page_obj = pending_paginator.page(pending_paginator.num_pages)

    interview_paginator = Paginator(upcoming_interviews_qs.order_by('interview_date'), 5)
    try:
        interview_page_obj = interview_paginator.page(interview_page_number)
    except PageNotAnInteger:
        interview_page_obj = interview_paginator.page(1)
    except EmptyPage:
        interview_page_obj = interview_paginator.page(interview_paginator.num_pages)

    pending_applications = pending_page_obj
    upcoming_interviews = interview_page_obj
    
    context = {
        'total_applications': total_applications,
        'shortlisted_count': shortlisted_count,
        'interviews_count': interviews_count,
        'placements_count': placements_count,
        'pending_applications': pending_applications,
        'upcoming_interviews': upcoming_interviews,
        'q': q,
        'status_filter': status_filter,
        'mode_filter': mode_filter,
        'time_filter': time_filter,
        'time_filter_options': DASHBOARD_TIME_FILTER_OPTIONS,
        'application_status_choices': Application.STATUS_CHOICES,
        'interview_mode_options': interview_mode_options,
        'pending_page_obj': pending_page_obj,
        'interview_page_obj': interview_page_obj,
    }

    return render(request, "main/dashboards/recruiter.html", context)


@login_required
def client_dashboard(request):
    if not hasattr(request.user, "client"):
        return _redirect_forbidden(request)

    client = request.user.client
    q = request.GET.get("q", "").strip()
    job_status_filter = request.GET.get("job_status", "all").strip().lower()
    mode_filter = request.GET.get("mode", "").strip()
    time_filter = request.GET.get("time_filter", "all")
    jobs_page_number = request.GET.get("jobs_page", 1)
    interview_page_number = request.GET.get("interview_page", 1)

    time_filter, start_dt, end_dt, now = _get_dashboard_time_window(time_filter)

    if job_status_filter not in {"all", "active", "closed"}:
        job_status_filter = "all"

    interview_mode_options = list(
        Interview.objects.filter(job__client=client)
        .exclude(mode__isnull=True)
        .exclude(mode__exact="")
        .order_by("mode")
        .values_list("mode", flat=True)
        .distinct()
    )

    client_jobs = Job.objects.filter(client=client)
    if start_dt is not None:
        client_jobs = client_jobs.filter(created_at__gte=start_dt)
    
    # Active jobs count
    active_jobs = client_jobs.filter(is_active=True).count()
    
    applications_base_qs = Application.objects.filter(job__client=client)
    if start_dt is not None:
        applications_base_qs = applications_base_qs.filter(applied_at__gte=start_dt)

    # Total applications to client's jobs
    total_applications = applications_base_qs.count()
    
    # Pending applications (waiting for review)
    pending_applications = applications_base_qs.filter(status='APPLIED').count()
    
    # Scheduled interviews (upcoming interviews for client's jobs)
    scheduled_interviews_qs = Interview.objects.filter(
        job__client=client,
        interview_date__gte=now
    )
    if end_dt is not None:
        scheduled_interviews_qs = scheduled_interviews_qs.filter(interview_date__lte=end_dt)
    scheduled_interviews = scheduled_interviews_qs.count()
    
    recent_jobs_qs = client_jobs

    upcoming_interviews_qs = Interview.objects.filter(
        job__client=client,
        interview_date__gte=now
    ).select_related('candidate', 'job')

    if end_dt is not None:
        upcoming_interviews_qs = upcoming_interviews_qs.filter(interview_date__lte=end_dt)

    if q:
        recent_jobs_qs = recent_jobs_qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(location__icontains=q)
        )

        upcoming_interviews_qs = upcoming_interviews_qs.filter(
            Q(candidate__user__first_name__icontains=q) |
            Q(candidate__user__last_name__icontains=q) |
            Q(candidate__user__username__icontains=q) |
            Q(job__title__icontains=q)
        )

    if job_status_filter == "active":
        recent_jobs_qs = recent_jobs_qs.filter(is_active=True)
    elif job_status_filter == "closed":
        recent_jobs_qs = recent_jobs_qs.filter(is_active=False)

    if mode_filter:
        upcoming_interviews_qs = upcoming_interviews_qs.filter(mode__iexact=mode_filter)

    jobs_paginator = Paginator(recent_jobs_qs.order_by('-created_at'), 5)
    try:
        jobs_page_obj = jobs_paginator.page(jobs_page_number)
    except PageNotAnInteger:
        jobs_page_obj = jobs_paginator.page(1)
    except EmptyPage:
        jobs_page_obj = jobs_paginator.page(jobs_paginator.num_pages)

    recent_jobs = jobs_page_obj

    for job in recent_jobs:
        job.application_count = Application.objects.filter(job=job).count()

    interview_paginator = Paginator(upcoming_interviews_qs.order_by('interview_date'), 5)
    try:
        interview_page_obj = interview_paginator.page(interview_page_number)
    except PageNotAnInteger:
        interview_page_obj = interview_paginator.page(1)
    except EmptyPage:
        interview_page_obj = interview_paginator.page(interview_paginator.num_pages)

    upcoming_interviews = interview_page_obj
    
    context = {
        'active_jobs': active_jobs,
        'total_applications': total_applications,
        'pending_applications': pending_applications,
        'scheduled_interviews': scheduled_interviews,
        'recent_jobs': recent_jobs,
        'upcoming_interviews': upcoming_interviews,
        'q': q,
        'job_status_filter': job_status_filter,
        'mode_filter': mode_filter,
        'time_filter': time_filter,
        'time_filter_options': DASHBOARD_TIME_FILTER_OPTIONS,
        'interview_mode_options': interview_mode_options,
        'jobs_page_obj': jobs_page_obj,
        'interview_page_obj': interview_page_obj,
    }

    return render(request, "main/dashboards/client.html", context)


@login_required
def candidate_dashboard(request):
    if not hasattr(request.user, "candidate"):
        return _redirect_forbidden(request)

    # live counts for candidate dashboard
    candidate = request.user.candidate
    q = request.GET.get("q", "").strip()
    job_type_filter = request.GET.get("job_type", "").strip()
    location_filter = request.GET.get("location", "").strip()
    time_filter = request.GET.get("time_filter", "all")
    jobs_page_number = request.GET.get("jobs_page", 1)

    time_filter, start_dt, end_dt, now = _get_dashboard_time_window(time_filter)

    job_type_options = list(
        Job.objects.filter(is_active=True)
        .exclude(job_type__isnull=True)
        .exclude(job_type__exact="")
        .order_by("job_type")
        .values_list("job_type", flat=True)
        .distinct()
    )

    applications_base_qs = Application.objects.filter(candidate=candidate)
    if start_dt is not None:
        applications_base_qs = applications_base_qs.filter(applied_at__gte=start_dt)

    my_applications_count = applications_base_qs.count()

    interviews_qs = Interview.objects.filter(candidate=candidate, interview_date__gte=now)
    if end_dt is not None:
        interviews_qs = interviews_qs.filter(interview_date__lte=end_dt)
    interviews_count = interviews_qs.count()

    # offers = applications with status SELECTED
    offers_count = applications_base_qs.filter(status='SELECTED').count()

    # basic profile-strength heuristic (percentage of important fields filled)
    checks = [
        bool(request.user.first_name or request.user.last_name),
        bool(request.user.email),
        bool(candidate.phone),
        bool(candidate.resume),
        bool(candidate.profile_picture),
        bool(candidate.skills),
        bool(candidate.experience),
    ]
    completed = sum(1 for ok in checks if ok)
    profile_strength = int((completed / len(checks)) * 100) if checks else 0

    show_job_results = bool(q or job_type_filter or location_filter or time_filter != "all")
    job_search_results = Job.objects.none()
    jobs_page_obj = None
    if show_job_results:
        jobs_qs = Job.objects.filter(is_active=True).select_related("client")

        if start_dt is not None:
            jobs_qs = jobs_qs.filter(created_at__gte=start_dt)

        if q:
            jobs_qs = jobs_qs.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(location__icontains=q) |
                Q(client__company_name__icontains=q)
            )

        if job_type_filter:
            jobs_qs = jobs_qs.filter(job_type__iexact=job_type_filter)

        if location_filter:
            jobs_qs = jobs_qs.filter(location__icontains=location_filter)

        jobs_paginator = Paginator(jobs_qs.order_by('-created_at'), 8)
        try:
            jobs_page_obj = jobs_paginator.page(jobs_page_number)
        except PageNotAnInteger:
            jobs_page_obj = jobs_paginator.page(1)
        except EmptyPage:
            jobs_page_obj = jobs_paginator.page(jobs_paginator.num_pages)

        job_search_results = jobs_page_obj

    context = {
        'my_applications_count': my_applications_count,
        'interviews_count': interviews_count,
        'offers_count': offers_count,
        'profile_strength': profile_strength,
        'q': q,
        'job_search_results': job_search_results,
        'job_type_filter': job_type_filter,
        'location_filter': location_filter,
        'time_filter': time_filter,
        'time_filter_options': DASHBOARD_TIME_FILTER_OPTIONS,
        'job_type_options': job_type_options,
        'show_job_results': show_job_results,
        'jobs_page_obj': jobs_page_obj,
    }

    return render(request, "main/dashboards/candidate.html", context)









@login_required
def recruiter_applications(request):

    if not hasattr(request.user, "stakeholder"):
        return _redirect_forbidden(request, "Only recruiters are allowed.")

    if request.user.stakeholder.role not in ["RECRUITER", "OWNER", "DEV_QA"]:
        return _redirect_forbidden(request, "Unauthorized role.")

    # -- search
    q = request.GET.get('q', '').strip()

    base_qs = Application.objects.select_related(
        "candidate", "job", "job__client", "interview"
    ).order_by('-applied_at')

    applications_qs = base_qs
    if q:
        applications_qs = base_qs.filter(
            Q(candidate__user__first_name__icontains=q) |
            Q(candidate__user__last_name__icontains=q) |
            Q(candidate__user__username__icontains=q) |
            Q(candidate__user__email__icontains=q) |
            Q(job__title__icontains=q) |
            Q(job__client__company_name__icontains=q)
        )

    total_applications = base_qs.count()
    pending_applications = base_qs.filter(status="APPLIED").count()
    shortlisted_applications = base_qs.filter(status="SHORTLISTED").count()
    scheduled_interviews = base_qs.filter(status="INTERVIEWED").count()

    # -- pagination (10 per page)
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(applications_qs, 10)
    page = request.GET.get('page', 1)
    try:
        applications_page = paginator.page(page)
    except PageNotAnInteger:
        applications_page = paginator.page(1)
    except EmptyPage:
        applications_page = paginator.page(paginator.num_pages)

    return render(request, "main/recruiter_applications.html", {
        "applications": applications_page,  # paginated page (iterable)
        "page_obj": applications_page,
        "paginator": paginator,
        "q": q,
        "total_applications": total_applications,
        "pending_applications": pending_applications,
        "shortlisted_applications": shortlisted_applications,
        "scheduled_interviews": scheduled_interviews,
    })


def jobs_api(request):
    jobs = Job.objects.filter(is_active=True).select_related("client").annotate(
        company=F("client__company_name")
    ).values(
        "id",
        "title",
        "company"
    )

    return JsonResponse(list(jobs), safe=False)


def job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id, is_active=True)
    return render(request, "main/job_detail.html", {"job": job})


@login_required
def view_application_resume(request, application_id):
    """Let recruiter or client (job owner) view the candidate's resume for an application."""
    application = get_object_or_404(Application, id=application_id)
    if not application.resume:
        raise Http404("No resume uploaded for this application.")

    # Permission: recruiter (OWNER/RECRUITER/DEV_QA) or client who owns the job
    can_view = False
    if hasattr(request.user, "stakeholder") and request.user.stakeholder.role in ["OWNER", "RECRUITER", "DEV_QA"]:
        can_view = True
    if hasattr(request.user, "client") and application.job.client_id == request.user.client.id:
        can_view = True

    if not can_view:
        return _redirect_forbidden(request)

    try:
        resume_file = application.resume.open("rb")
    except (ValueError, FileNotFoundError):
        raise Http404("Resume file not found.")

    name = application.resume.name
    content_type = "application/pdf"
    if name and name.lower().endswith(".doc"):
        content_type = "application/msword"
    elif name and name.lower().endswith(".docx"):
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    response = FileResponse(resume_file, content_type=content_type, as_attachment=False)
    response["Content-Disposition"] = "inline; filename=\"" + (os.path.basename(name) if name else "resume") + "\""
    return response


@login_required
def job_applications(request, job_id):
    """Client view: list applications for one of their jobs. Recruiters can also view."""
    job = get_object_or_404(Job, id=job_id)
    can_view = False
    if hasattr(request.user, "client") and job.client_id == request.user.client.id:
        can_view = True
    if hasattr(request.user, "stakeholder") and request.user.stakeholder.role in ["OWNER", "RECRUITER", "DEV_QA"]:
        can_view = True
    if not can_view:
        return _redirect_forbidden(request)

    can_schedule = False
    if hasattr(request.user, "stakeholder") and request.user.stakeholder.role in ["OWNER", "RECRUITER", "DEV_QA"]:
        can_schedule = True

    can_update_status = False
    if can_schedule:
        can_update_status = True
    if hasattr(request.user, "client") and job.client_id == request.user.client.id:
        can_update_status = True

    applications = Application.objects.filter(job=job).select_related("candidate", "candidate__user")
    under_review = applications.filter(status="APPLIED").count()
    interviews_scheduled = Interview.objects.filter(job=job, interview_date__isnull=False).count()
    return render(
        request,
        "main/job_applications.html",
        {
            "job": job,
            "applications": applications,
            "under_review": under_review,
            "interviews_scheduled": interviews_scheduled,
            "can_schedule": can_schedule,
            "can_update_status": can_update_status,
        },
    )


@login_required
@role_required("client")
def client_feedback(request, application_id):
    application = get_object_or_404(Application, id=application_id)

    if application.job.client_id != request.user.client.id:
        return _redirect_forbidden(request)

    existing_feedback = ClientFeedback.objects.filter(
        job=application.job,
        candidate=application.candidate,
    ).first()

    if request.method == "POST":
        form = EnhancedFeedbackForm(request.POST, instance=existing_feedback)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.job = application.job
            feedback.candidate = application.candidate
            feedback.save()
            messages.success(request, "Client feedback saved successfully.")
            return redirect("job_applications", job_id=application.job.id)
    else:
        form = EnhancedFeedbackForm(instance=existing_feedback)

    return render(
        request,
        "main/client_feedback.html",
        {
            "form": form,
            "application": application,
            "existing_feedback": existing_feedback,
        },
    )





@login_required
def application_detail(request, application_id):
    """View details of a specific application"""
    application = get_object_or_404(Application, id=application_id)
    
    # Check permissions: recruiter, client who owns the job, or the candidate
    can_view = False
    if hasattr(request.user, "stakeholder") and request.user.stakeholder.role in ["OWNER", "RECRUITER", "DEV_QA"]:
        can_view = True
    if hasattr(request.user, "client") and application.job.client_id == request.user.client.id:
        can_view = True
    if hasattr(request.user, "candidate") and application.candidate_id == request.user.candidate.id:
        can_view = True
    
    if not can_view:
        return _redirect_forbidden(request)
    
    return render(request, "main/application_detail.html", {"application": application})


@login_required
def remove_interview_datetime(request, interview_id):

    # 🔐 Only recruiter / stakeholder
    if not hasattr(request.user, "stakeholder"):
        return _redirect_forbidden(request, "Only recruiters are allowed.")

    interview = get_object_or_404(Interview, id=interview_id)

    if request.method == "POST":
        interview.interview_date = None
        interview.save(update_fields=["interview_date"])
        return redirect("recruiter_applications")

    return HttpResponse("Invalid request", status=400)


@login_required
def job_edit(request, job_id):
    """Edit a job posting"""
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the client who posted this job
    if not hasattr(request.user, 'client') or request.user.client != job.client:
        return _redirect_forbidden(request)
    
    if request.method == "POST":
        job.title = request.POST.get('title', job.title)
        job.description = request.POST.get('description', job.description)
        job.location = request.POST.get('location', job.location)
        job.salary = request.POST.get('salary', job.salary)
        job.is_active = request.POST.get('is_active') == 'on'
        job.save()
        return redirect('job_detail', job_id=job.id)
    
    return render(request, 'main/job_edit.html', {'job': job})


@login_required
def company_settings(request):
    """Company/Client settings page"""
    if not hasattr(request.user, 'client'):
        return _redirect_forbidden(request, "Only clients can access company settings.")
    
    client = request.user.client
    
    if request.method == "POST":
        client.company_name = request.POST.get('company_name', client.company_name)
        client.contact_number = request.POST.get('contact_number', client.contact_number)
        
        # Handle company logo upload
        if request.FILES.get('company_logo'):
            client.company_logo = request.FILES.get('company_logo')
        
        # Handle profile picture upload
        if request.FILES.get('profile_picture'):
            client.profile_picture = request.FILES.get('profile_picture')
        
        client.save()
        return redirect('client_dashboard')
    
    return render(request, 'main/company_settings.html', {'client': client})


# ====================================================
# PDF EXPORT FUNCTIONS
# ====================================================
@login_required
def export_client_placements_pdf(request):
    """Export client placements report as PDF"""
    try:
        # Get data
        data = Client.objects.annotate(
            placements=Count("jobs__applications", filter=Q(jobs__applications__status="SELECTED"), distinct=True)
        ).values('company_name', 'placements')
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, title="Client Placements Report")
        story = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0d6efd'),
            spaceBefore=12,
            spaceAfter=12,
        )
        
        # Add title
        story.append(Paragraph("Client Placements Report", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Create table data
        table_data = [['Company Name', 'Placements']]
        for row in data:
            table_data.append([row['company_name'], str(row['placements'])])
        
        # Create and style table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        
        # Return PDF
        buffer.seek(0)
        return FileResponse(
            buffer,
            as_attachment=True,
            filename='client_placements_report.pdf',
            content_type='application/pdf'
        )
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@login_required
def export_recruiter_performance_pdf(request):
    """Export recruiter performance report as PDF"""
    try:
        # Get data for recruiter performance
        recruiters_data = Stakeholder.objects.filter(
            role__in=['RECRUITER']
        ).annotate(
            applications_handled=Count('user__interview', distinct=True),
            interviews_scheduled=Count('user__interview__application', distinct=True),
        )
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, title="Recruiter Performance Report")
        story = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0d6efd'),
            spaceBefore=12,
            spaceAfter=12,
        )
        
        # Add title
        story.append(Paragraph("Recruiter Performance Report", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Create table data
        table_data = [['Recruiter', 'Applications Handled', 'Interviews Scheduled']]
        for recruiter in recruiters_data:
            table_data.append([
                recruiter.user.get_full_name() or recruiter.user.username,
                str(recruiter.applications_handled),
                str(recruiter.interviews_scheduled),
            ])
        
        # Create and style table
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(table)
        doc.build(story)
        
        # Return PDF
        buffer.seek(0)
        return FileResponse(
            buffer,
            as_attachment=True,
            filename='recruiter_performance_report.pdf',
            content_type='application/pdf'
        )
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@login_required
def _placeholder_for_removed_admin_functions():
    # Custom admin dashboard and toggle functions were removed to use Django's
    # built-in admin site. This placeholder prevents accidental name reuse.
    return None