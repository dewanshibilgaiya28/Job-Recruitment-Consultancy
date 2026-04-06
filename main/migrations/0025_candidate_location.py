from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0024_client_company_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidate',
            name='location',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
