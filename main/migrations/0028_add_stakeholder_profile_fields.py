from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0027_add_stakeholder_profile_picture"),
    ]

    operations = [
        migrations.AddField(
            model_name="stakeholder",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="stakeholder",
            name="location",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="stakeholder",
            name="skills",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="stakeholder",
            name="experience",
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
