from django.contrib import admin
from django import forms
from .models import (
    Client, Candidate, Job, Application, Stakeholder, Interview, 
    ClientFeedback, Feedback, AuditLog
)

# Register your models here
class ClientAdminForm(forms.ModelForm):
    first_name = forms.CharField(required=False, label='First Name')
    last_name = forms.CharField(required=False, label='Last Name')
    email = forms.EmailField(required=False, label='Email')

    class Meta:
        model = Client
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.user_id:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        client = super().save(commit=False)
        user = client.user
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data.get('email', '')

        if commit:
            user.save()
            client.save()
            self.save_m2m()

        return client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    form = ClientAdminForm
    list_display = (
        'company_name',
        'first_name_display',
        'last_name_display',
        'email_display',
        'contact_number',
        'created_at',
    )
    search_fields = (
        'company_name',
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'contact_number',
    )
    list_filter = ('created_at',)
    fields = (
        'user',
        'first_name',
        'last_name',
        'email',
        'user_type_display',
        'company_name',
        'contact_number',
        'company_logo',
        'profile_picture',
        'location_na',
        'skills_na',
        'experience_na',
    )
    readonly_fields = ('user_type_display', 'location_na', 'skills_na', 'experience_na')

    @admin.display(description='First Name', ordering='user__first_name')
    def first_name_display(self, obj):
        return obj.user.first_name

    @admin.display(description='Last Name', ordering='user__last_name')
    def last_name_display(self, obj):
        return obj.user.last_name

    @admin.display(description='Email', ordering='user__email')
    def email_display(self, obj):
        return obj.user.email

    @admin.display(description='User Type')
    def user_type_display(self, obj):
        return 'Employer'

    @admin.display(description='Location')
    def location_na(self, obj):
        return 'Not applicable'

    @admin.display(description='Skills')
    def skills_na(self, obj):
        return 'Not applicable'

    @admin.display(description='Experience')
    def experience_na(self, obj):
        return 'Not applicable'

class CandidateAdminForm(forms.ModelForm):
    first_name = forms.CharField(required=False, label='First Name')
    last_name = forms.CharField(required=False, label='Last Name')
    email = forms.EmailField(required=False, label='Email')

    class Meta:
        model = Candidate
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.user_id:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        candidate = super().save(commit=False)
        user = candidate.user
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data.get('email', '')

        if commit:
            user.save()
            candidate.save()
            self.save_m2m()

        return candidate


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    form = CandidateAdminForm
    list_display = (
        'user',
        'first_name_display',
        'last_name_display',
        'email_display',
        'phone',
        'location',
        'experience',
        'created_at',
    )
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'phone',
        'location',
        'skills',
    )
    list_filter = ('experience', 'created_at')
    fields = (
        'user',
        'first_name',
        'last_name',
        'email',
        'user_type_display',
        'phone',
        'location',
        'skills',
        'experience',
        'resume',
        'profile_picture',
    )
    readonly_fields = ('user_type_display',)

    @admin.display(description='First Name', ordering='user__first_name')
    def first_name_display(self, obj):
        return obj.user.first_name

    @admin.display(description='Last Name', ordering='user__last_name')
    def last_name_display(self, obj):
        return obj.user.last_name

    @admin.display(description='Email', ordering='user__email')
    def email_display(self, obj):
        return obj.user.email

    @admin.display(description='User Type')
    def user_type_display(self, obj):
        return 'Candidate'

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'location', 'job_type', 'is_active', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('is_active', 'job_type', 'created_at')

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'status', 'applied_at')
    search_fields = ('candidate__user__username', 'job__title')
    list_filter = ('status', 'applied_at')

class StakeholderAdminForm(forms.ModelForm):
    first_name = forms.CharField(required=False, label='First Name')
    last_name = forms.CharField(required=False, label='Last Name')
    email = forms.EmailField(required=False, label='Email')

    class Meta:
        model = Stakeholder
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.user_id:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        stakeholder = super().save(commit=False)
        user = stakeholder.user
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data.get('email', '')

        if commit:
            user.save()
            stakeholder.save()
            self.save_m2m()

        return stakeholder


@admin.register(Stakeholder)
class StakeholderAdmin(admin.ModelAdmin):
    form = StakeholderAdminForm
    list_display = ('user', 'first_name_display', 'last_name_display', 'email_display', 'role', 'phone', 'location', 'experience')
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'role',
        'phone',
        'location',
        'skills',
    )
    list_filter = ('role', 'experience')
    fields = ('user', 'first_name', 'last_name', 'email', 'role', 'profile_picture', 'phone', 'location', 'skills', 'experience')

    @admin.display(description='First Name', ordering='user__first_name')
    def first_name_display(self, obj):
        return obj.user.first_name

    @admin.display(description='Last Name', ordering='user__last_name')
    def last_name_display(self, obj):
        return obj.user.last_name

    @admin.display(description='Email', ordering='user__email')
    def email_display(self, obj):
        return obj.user.email

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job', 'interview_date', 'mode')
    search_fields = ('candidate__user__username', 'job__title')
    list_filter = ('interview_date', 'mode')

@admin.register(ClientFeedback)
class ClientFeedbackAdmin(admin.ModelAdmin):
    list_display = ('job', 'candidate', 'created_at')
    search_fields = ('job__title', 'candidate__user__username')
    list_filter = ('created_at',)

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'created_at')
    search_fields = ('user__username', 'message')
    list_filter = ('rating', 'created_at')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'resource_type', 'timestamp')
    search_fields = ('user__username', 'action', 'resource_type')
    list_filter = ('action', 'status', 'timestamp')
    readonly_fields = ('timestamp',)
