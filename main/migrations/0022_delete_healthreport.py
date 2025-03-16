from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0021_notification'),
    ]

    operations = [
        migrations.DeleteModel(
            name='HealthReport',
        ),
    ]
