from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("analise", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Users",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("email", models.EmailField(db_index=True, max_length=254, unique=True)),
                (
                    "role",
                    models.CharField(
                        choices=[("ADMIN", "Admin"), ("USER", "User")],
                        default="USER",
                        max_length=10,
                    ),
                ),
                ("password", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "users",
                "ordering": ["-created_at"],
            },
        ),
    ]
