# Generated by Django 5.1.7 on 2025-03-13 16:43

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0008_systemalert'),
    ]

    operations = [
        migrations.CreateModel(
            name='Recommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recommendation_text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doctor_recommendations', to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='patient_recommendations', to=settings.AUTH_USER_MODEL)),
                ('risk_assessment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.riskassessment')),
            ],
        ),
    ]
