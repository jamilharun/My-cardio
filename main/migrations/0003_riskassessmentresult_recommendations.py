# Generated by Django 5.1.7 on 2025-03-10 02:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_riskassessmentresult'),
    ]

    operations = [
        migrations.AddField(
            model_name='riskassessmentresult',
            name='recommendations',
            field=models.TextField(blank=True, null=True),
        ),
    ]
