# Generated manually to add FK fields that are missing from the DB schema
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def _column_exists(schema_editor, table_name, column_name):
    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(cursor, table_name)
    return any(column.name == column_name for column in columns)


def _constraint_exists(schema_editor, table_name, constraint_name):
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(cursor, table_name)
    return constraint_name in constraints


def _add_field_if_missing(apps, schema_editor, model_label, field_name):
    app_label, model_name = model_label.split(".")
    model = apps.get_model(app_label, model_name)
    table_name = model._meta.db_table
    field = model._meta.get_field(field_name)
    if not _column_exists(schema_editor, table_name, field.column):
        schema_editor.add_field(model, field)


def _add_index_if_missing(apps, schema_editor, model_label, index):
    app_label, model_name = model_label.split(".")
    model = apps.get_model(app_label, model_name)
    table_name = model._meta.db_table
    if not _constraint_exists(schema_editor, table_name, index.name):
        schema_editor.add_index(model, index)


def add_missing_fields_and_indexes(apps, schema_editor):
    _add_field_if_missing(apps, schema_editor, "main.AuditLog", "user")
    _add_field_if_missing(apps, schema_editor, "main.ClientPerformance", "client")
    _add_field_if_missing(apps, schema_editor, "main.PlacementTracker", "hired_candidate")
    _add_field_if_missing(apps, schema_editor, "main.PlacementTracker", "job")
    _add_field_if_missing(apps, schema_editor, "main.RecruiterPerformance", "recruiter")

    _add_index_if_missing(
        apps,
        schema_editor,
        "main.AuditLog",
        models.Index(fields=["user", "-timestamp"], name="main_auditl_user_id_5c7864_idx"),
    )
    _add_index_if_missing(
        apps,
        schema_editor,
        "main.PlacementTracker",
        models.Index(fields=["job", "status"], name="main_placem_job_id_87b240_idx"),
    )
    _add_index_if_missing(
        apps,
        schema_editor,
        "main.PlacementTracker",
        models.Index(fields=["status", "-created_at"], name="main_placem_status_8d2880_idx"),
    )
    _add_index_if_missing(
        apps,
        schema_editor,
        "main.ClientPerformance",
        models.Index(fields=["client"], name="main_client_client__5b9e09_idx"),
    )
    _add_index_if_missing(
        apps,
        schema_editor,
        "main.RecruiterPerformance",
        models.Index(fields=["recruiter"], name="main_recrui_recruit_f0ebb6_idx"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0020_auditlog_clientperformance_pipelinemetrics_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_missing_fields_and_indexes, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='auditlog',
                    name='user',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
                ),
                migrations.AddField(
                    model_name='clientperformance',
                    name='client',
                    field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='performance_metrics', to='main.client'),
                ),
                migrations.AddField(
                    model_name='placementtracker',
                    name='hired_candidate',
                    field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.candidate'),
                ),
                migrations.AddField(
                    model_name='placementtracker',
                    name='job',
                    field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='placement_tracker', to='main.job'),
                ),
                migrations.AddField(
                    model_name='recruiterperformance',
                    name='recruiter',
                    field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='performance_metrics', to=settings.AUTH_USER_MODEL),
                ),
                migrations.AddIndex(
                    model_name='auditlog',
                    index=models.Index(fields=['user', '-timestamp'], name='main_auditl_user_id_5c7864_idx'),
                ),
                migrations.AddIndex(
                    model_name='placementtracker',
                    index=models.Index(fields=['job', 'status'], name='main_placem_job_id_87b240_idx'),
                ),
                migrations.AddIndex(
                    model_name='placementtracker',
                    index=models.Index(fields=['status', '-created_at'], name='main_placem_status_8d2880_idx'),
                ),
                migrations.AddIndex(
                    model_name='clientperformance',
                    index=models.Index(fields=['client'], name='main_client_client__5b9e09_idx'),
                ),
                migrations.AddIndex(
                    model_name='recruiterperformance',
                    index=models.Index(fields=['recruiter'], name='main_recrui_recruit_f0ebb6_idx'),
                ),
            ],
        ),
    ]
