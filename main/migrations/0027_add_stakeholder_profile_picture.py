from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0026_remove_unused_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="stakeholder",
            name="profile_picture",
            field=models.ImageField(blank=True, null=True, upload_to="profile_pictures/%Y/%m/"),
        ),
    ]
