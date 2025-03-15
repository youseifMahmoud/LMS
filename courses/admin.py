from django.contrib import admin
from .models import Course, Lesson, Enrollment, LessonProgress, UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role']  # تغيير is_teacher إلى role أو is_instructor
    list_filter = ['role']
    search_fields = ['user__username', 'user__email']

class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'instructor', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'description', 'instructor__username']

class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    list_filter = ['course']
    search_fields = ['title', 'content', 'course__title']

class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'enrolled_at', 'completed']
    list_filter = ['enrolled_at', 'completed']
    search_fields = ['user__username', 'course__title']

class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'completed']
    list_filter = ['completed']
    search_fields = ['user__username', 'lesson__title']

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(LessonProgress, LessonProgressAdmin)