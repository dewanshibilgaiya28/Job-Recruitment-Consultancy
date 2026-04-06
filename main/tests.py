from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Client as ClientModel, Job, Candidate


class JobSearchTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='client1', password='pass')
        self.client_obj = ClientModel.objects.create(user=user, company_name='Acme Corp', contact_number='123')

        # active job
        Job.objects.create(
            client=self.client_obj,
            title='Python Developer',
            description='Experienced Django developer',
            location='Remote',
            is_active=True
        )

        # inactive job (should not appear in search results)
        Job.objects.create(
            client=self.client_obj,
            title='Java Engineer',
            description='Java backend role',
            location='NY',
            is_active=False
        )

    def test_search_by_title(self):
        resp = self.client.get(reverse('job_search') + '?q=Python')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Python Developer')
        self.assertNotContains(resp, 'Java Engineer')

    def test_search_by_description(self):
        resp = self.client.get(reverse('job_search') + '?q=Django')
        self.assertContains(resp, 'Python Developer')

    def test_search_by_company(self):
        resp = self.client.get(reverse('job_search') + '?q=Acme')
        self.assertContains(resp, 'Python Developer')

    def test_empty_query_returns_active_jobs(self):
        resp = self.client.get(reverse('job_search'))
        self.assertContains(resp, 'Python Developer')
        self.assertNotContains(resp, 'Java Engineer')


class ProfileRoleTests(TestCase):
    def test_client_login_redirects_to_client_dashboard(self):
        user = User.objects.create_user(username='client_login', password='pass')
        ClientModel.objects.create(user=user, company_name='ACME', contact_number='111')

        resp = self.client.post(reverse('login'), {'username': 'client_login', 'password': 'pass'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('client_dashboard'))

    def test_profile_shows_client_when_user_has_both_candidate_and_client(self):
        user = User.objects.create_user(
            username='dual_user', password='pass', first_name='Dual', last_name='User', email='dual@example.com'
        )
        ClientModel.objects.create(user=user, company_name='DualCorp', contact_number='999')
        Candidate.objects.create(user=user, phone='555', skills='python', experience=2)

        # login and fetch profile
        self.client.login(username='dual_user', password='pass')
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 200)

        # Profile must render as CLIENT (Employer) and show client contact, not candidate-only fields
        self.assertContains(resp, 'Employer')
        self.assertContains(resp, '999')
        self.assertNotContains(resp, '555')
        self.assertContains(resp, 'Not applicable')

    def test_client_can_upload_profile_picture_and_displayed(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # create client user
        user = User.objects.create_user(username='client_photo', password='pass')
        client = ClientModel.objects.create(user=user, company_name='LogoCorp', contact_number='321')

        self.client.login(username='client_photo', password='pass')

        # create a tiny PNG in memory
        img_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\x0b\xbf\x02\x8b\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        upload = SimpleUploadedFile('logo.png', img_bytes, content_type='image/png')

        resp = self.client.post(reverse('company_settings'), {
            'company_name': client.company_name,
            'contact_number': client.contact_number,
            'profile_picture': upload,
        })
        self.assertEqual(resp.status_code, 302)
        client.refresh_from_db()
        self.assertTrue(client.profile_picture)

        # profile page should render the uploaded image URL
        resp = self.client.get(reverse('profile'))
        self.assertContains(resp, client.profile_picture.url)
