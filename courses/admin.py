from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count
from .models import (
    Course, Lesson, Enrollment, LessonProgress, 
    UserProfile, LessonAttachment
)

# إدارة الملف الشخصي للمستخدم مع إمكانية تعديل الدور
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'الملف الشخصي'
    fk_name = 'user'

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff', 'is_active')
    list_select_related = ('profile',)
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'profile__role')
    search_fields = ('username', 'email', 'profile__role')

    def get_role(self, instance):
        return instance.profile.role
    get_role.short_description = 'الصلاحية'

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# إدارة UserProfile بشكل مستقل (اختياري)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email']

admin.site.register(UserProfile, UserProfileAdmin)

# إدارة المرفقات داخل الدرس
class LessonAttachmentInline(admin.TabularInline):
    model = LessonAttachment
    extra = 1

# إدارة الدروس داخل الكورس
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ['title', 'content', 'order']

# إدارة الكورسات
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'instructor', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'description', 'instructor__username']
    inlines = [LessonInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "instructor":
            kwargs["queryset"] = User.objects.filter(profile__role='instructor')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# إدارة الدروس مع المرفقات
class LessonAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order']
    list_filter = ['course']
    search_fields = ['title', 'content', 'course__title']
    inlines = [LessonAttachmentInline]

# إدارة التسجيل في الكورسات
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['course_name', 'enrollment_count', 'enrolled_at', 'completed']
    list_filter = ['enrolled_at', 'completed', 'course']
    search_fields = ['course__title', 'user__username']

    def course_name(self, obj):
        return obj.course.title
    course_name.short_description = 'الكورس'

    def enrollment_count(self, obj):
        return Enrollment.objects.filter(course=obj.course).count()
    enrollment_count.short_description = 'عدد المسجلين'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('course')

# إدارة تقدم الطلاب في الدروس
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'completed']
    list_filter = ['completed']
    search_fields = ['user__username', 'lesson__title']

admin.site.register(Course, CourseAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(LessonProgress, LessonProgressAdmin)
