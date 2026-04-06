from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0025_candidate_location"),
    ]

    operations = [
        migrations.DeleteModel(name="JobApproval"),
        migrations.DeleteModel(name="RecruiterNote"),
        migrations.DeleteModel(name="PlacementTracker"),
        migrations.DeleteModel(name="PipelineMetrics"),
        migrations.DeleteModel(name="RecruiterPerformance"),
        migrations.DeleteModel(name="ClientPerformance"),
        migrations.DeleteModel(name="SystemMetrics"),
    ]
