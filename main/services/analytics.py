from main.models import Job, Application

def analytics_summary():
    return {
        "total_jobs": Job.objects.count(),
        "total_applications": Application.objects.count()
    }
