# Generated manually to add profile_picture to Candidate
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0021_fix_missing_fks"),
    ]

    operations = [
        migrations.AddField(
            model_name="candidate",
            name="profile_picture",
            field=models.ImageField(upload_to='profile_pictures/%Y/%m/', null=True, blank=True),
        ),
    ]
