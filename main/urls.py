from django.urls import path
from . import views

urlpatterns = [
    path("favicon.ico", views.favicon, name="favicon"),
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/recruiter/", views.recruiter_dashboard, name="recruiter_dashboard"),
    path("dashboard/client/", views.client_dashboard, name="client_dashboard"),
    path("dashboard/candidate/", views.candidate_dashboard, name="candidate_dashboard"),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("candidate/register/", views.candidate_register, name="candidate_register"),
    path("client/register/", views.client_register, name="client_register"),

    path("job/post/", views.job_post, name="job_post"),
    path("job/<int:job_id>/edit/", views.job_edit, name="job_edit"),
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/search/", views.job_search, name="job_search"),
    path("jobs/filter/", views.job_filter, name="job_filter"),

    path("apply/<int:job_id>/", views.apply_job, name="apply_job"),
    path("applications/", views.my_applications, name="my_applications"),

    # path("schedule-interview/<int:app_id>/", views.schedule_interview),
    path("update-status/<int:app_id>/<str:new_status>/", views.update_status, name="update_status"),

    path("reports/active-jobs/", views.active_jobs_report, name="active_jobs_report"),
    path("reports/pipeline/", views.candidate_pipeline_report, name="candidate_pipeline_report"),
    path("reports/recruiter-performance/", views.recruiter_performance_report, name="recruiter_performance_report"),
    path("reports/client-placements/", views.client_placement_report, name="client_placements"),
    
    path("reports/export-client-placements-pdf/", views.export_client_placements_pdf, name="export_client_placements_pdf"),
    path("reports/export-recruiter-performance-pdf/", views.export_recruiter_performance_pdf, name="export_recruiter_performance_pdf"),


    path("recruiter/applications/", views.recruiter_applications, name="recruiter_applications"),
    path("application/<int:application_id>/", views.application_detail, name="application_detail"),
    path("application/<int:application_id>/client-feedback/", views.client_feedback, name="client_feedback"),
    path("schedule-interview/<int:application_id>/", views.schedule_interview, name="schedule_interview"),
    path("api/jobs/", views.jobs_api),
    path("jobs/<int:job_id>/", views.job_detail, name="job_detail"),
    path("jobs/<int:job_id>/applications/", views.job_applications, name="job_applications"),
    path("application/<int:application_id>/resume/", views.view_application_resume, name="view_application_resume"),

    path("interview/remove-datetime/<int:interview_id>/",views.remove_interview_datetime,name="remove_interview_datetime"),

    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("company-settings/", views.company_settings, name="company_settings"),

    # Candidate resources
    path("resources/resume-tips/", views.resume_tips, name="resume_tips"),
    path("resources/interview-prep/", views.interview_prep, name="interview_prep"),
    path("resources/job-search-guide/", views.job_search_guide, name="job_search_guide"),

    path("about/company-profile/", views.info_page, {"slug": "company_profile"}, name="company_profile"),
    path("about/leadership/", views.info_page, {"slug": "leadership"}, name="leadership"),
    path("about/csr/", views.info_page, {"slug": "csr"}, name="csr"),
    path("about/sustainability/", views.info_page, {"slug": "sustainability"}, name="sustainability"),
    path("services/general-staffing/", views.info_page, {"slug": "services_general_staffing"}, name="services_general_staffing"),
    path("services/professional-staffing/", views.info_page, {"slug": "services_professional_staffing"}, name="services_professional_staffing"),
    path("services/digital-platform/", views.info_page, {"slug": "services_digital_platform"}, name="services_digital_platform"),
    path("services/gcc/", views.info_page, {"slug": "services_gcc"}, name="services_gcc"),
    path("resources/blogs/", views.info_page, {"slug": "blogs"}, name="blogs"),
    path("resources/case-studies/", views.info_page, {"slug": "case_studies"}, name="case_studies"),
    path("resources/knowledge-base/", views.info_page, {"slug": "knowledge_base"}, name="knowledge_base"),
    path("investors/", views.info_page, {"slug": "investors"}, name="investors"),
    path("media/", views.info_page, {"slug": "media"}, name="media"),
    path("contact/", views.info_page, {"slug": "contact_us"}, name="contact_us"),

]
