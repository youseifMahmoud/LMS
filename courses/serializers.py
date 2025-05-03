from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Course, Lesson, Enrollment, LessonProgress

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'content', 'order', 'created_at']

class CourseSerializer(serializers.ModelSerializer):
    instructor = UserSerializer(read_only=True)
    lessons_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'instructor', 'created_at', 'image', 'lessons_count']
    
    def get_lessons_count(self, obj):
        return obj.lessons.count()

class CourseDetailSerializer(CourseSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    
    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ['lessons']

class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    progress = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'enrolled_at', 'completed', 'progress']
    
    def get_progress(self, obj):
        total_lessons = obj.course.lessons.count()
        if total_lessons == 0:
            return 0
        completed_lessons = LessonProgress.objects.filter(
            user=obj.user, 
            lesson__course=obj.course,
            completed=True
        ).count()
        return int((completed_lessons / total_lessons) * 100)

class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['id', 'lesson', 'completed', 'last_accessed']