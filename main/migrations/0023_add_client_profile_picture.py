from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0022_add_candidate_profile_picture"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="profile_picture",
            field=models.ImageField(upload_to='profile_pictures/%Y/%m/', null=True, blank=True),
        ),
    ]
