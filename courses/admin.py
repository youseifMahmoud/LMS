from django.contrib import admin
from .models import UserProfile, Course, Lesson, Enrollment, LessonProgress

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_teacher')

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Enrollment)
admin.site.register(LessonProgress)

# Register your models here.
