from rest_framework.generics import ListAPIView
from main.models import Job
from .serializers import JobSerializer

class JobListAPI(ListAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
