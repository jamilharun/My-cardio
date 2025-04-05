from django.contrib import admin
from .models import CustomUser, UserProfile, HealthHistory, RiskAssessmentResult

admin.site.register(CustomUser)
admin.site.register(UserProfile)
admin.site.register(HealthHistory)

@admin.register(RiskAssessmentResult)
class RiskAssessmentResultAdmin(admin.ModelAdmin):
    list_display = ("user", "age", "gender", "risk_level", "risk_probability", "created_at")
    search_fields = ("user__username", "risk_level")
    list_filter = ("risk_level", "created_at")