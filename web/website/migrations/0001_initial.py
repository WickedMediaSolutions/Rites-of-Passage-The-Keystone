# Generated migration for Phase 9 models: Ban, AuditLog, ReservedName
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_id", models.IntegerField(help_text="Account DB id of the acting admin/account.")),
                ("actor_name", models.CharField(help_text="Username at time of action.", max_length=255)),
                ("action", models.CharField(help_text="Short action category (ban, unban, etc.).", max_length=255)),
                ("target_type", models.CharField(blank=True, default="", max_length=64)),
                ("target_id", models.IntegerField(blank=True, null=True)),
                ("target_name", models.CharField(blank=True, default="", max_length=255)),
                ("details", models.TextField(blank=True, default="")),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Audit Log Entry",
                "verbose_name_plural": "Audit Log",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.CreateModel(
            name="Ban",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account_id", models.IntegerField(help_text="Account DB id of the banned account.", unique=True)),
                ("account_name", models.CharField(help_text="Username of the banned account, for display.", max_length=255)),
                ("reason", models.TextField(help_text="Reason displayed to the banned player and stored for audit.")),
                ("banned_by_id", models.IntegerField(help_text="Account DB id of the banning admin.")),
                ("banned_by_name", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Ban",
                "verbose_name_plural": "Bans",
            },
        ),
        migrations.CreateModel(
            name="ReservedName",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(help_text="Case-insensitive reserved name.", max_length=32, unique=True)),
                ("reason", models.CharField(default="Reserved", help_text="Why this name is reserved.", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Reserved Name",
                "verbose_name_plural": "Reserved Names",
            },
        ),
    ]