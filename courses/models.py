from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg , Sum
from django.db.models.signals import post_save
from django.dispatch import receiver
import subprocess
import json
import os

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='course_images/', null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    @property
    def average_rating(self):
        """حساب متوسط تقييم الدورة"""
        avg = self.ratings.aggregate(avg_rating=Avg('rating'))['avg_rating']
        return round(avg, 1) if avg else 0
    
    @property
    def total_students(self):
        """حساب إجمالي عدد الطلاب المسجلين في الدورة"""
        return self.enrollments.count()
    
    @property
    def total_duration_minutes(self):
        """حساب إجمالي مدة الدورة بالدقائق"""
        return self.lessons.aggregate(total=Sum('duration'))['total'] or 0
    
    @property
    def duration_text(self):
        """إرجاع نص المدة بتنسيق مناسب"""
        total_minutes = self.total_duration_minutes
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        if hours > 0:
            if minutes > 0:
                return f"{hours} ساعة و {minutes} دقيقة"
            else:
                return f"{hours} ساعة"
        else:
            return f"{minutes} دقيقة"
    


class Rating(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('course', 'user')
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title} - {self.rating}"

def lesson_attachment_path(instance, filename):
    # الملف سيتم حفظه في: MEDIA_ROOT/lesson_attachments/course_<id>/lesson_<id>/<filename>
    return f'lesson_attachments/course_{instance.lesson.course.id}/lesson_{instance.lesson.id}/{filename}'

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    content = models.TextField()
    video = models.FileField(upload_to='lesson_videos/', blank=True, null=True)
    duration = models.PositiveIntegerField(default=0, help_text="مدة الدرس بالدقائق")
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.title

class LessonAttachment(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='attachments')
    attachment_file = models.FileField(upload_to=lesson_attachment_path)
    filename = models.CharField(max_length=255, blank=True)
    file_type = models.CharField(max_length=10, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"مرفق {self.filename} للدرس {self.lesson.title}"
    
    def save(self, *args, **kwargs):
        if not self.filename and self.attachment_file:
            self.filename = os.path.basename(self.attachment_file.name)
        
        if self.attachment_file:
            ext = os.path.splitext(self.attachment_file.name)[1].lower()
            if ext in ['.pdf']:
                self.file_type = 'pdf'
            elif ext in ['.docx', '.doc']:
                self.file_type = 'docx'
            elif ext in ['.pptx', '.ppt']:
                self.file_type = 'pptx'
            elif ext in ['.zip']:
                self.file_type = 'zip'
            elif ext in ['.rar']:
                self.file_type = 'rar'
            else:
                self.file_type = 'other'
        
        super().save(*args, **kwargs)

class Quiz(models.Model):
    """نموذج الاختبار"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    time_limit = models.PositiveIntegerField(default=30, help_text="مدة الاختبار بالدقائق")
    passing_score = models.PositiveIntegerField(default=60, help_text="النسبة المئوية المطلوبة للنجاح")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.course.title}"
    
    @property
    def question_count(self):
        """عدد الأسئلة في الاختبار"""
        return self.questions.count()
    
    @property
    def max_score(self):
        """أقصى درجة يمكن الحصول عليها"""
        return self.question_count * 100
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "اختبار"
        verbose_name_plural = "اختبارات"


class Question(models.Model):
    """نموذج السؤال"""
    QUESTION_TYPES = [
        ('multiple_choice', 'اختيار من متعدد'),
        ('true_false', 'صح أم خطأ'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.text[:50]}..."
    
    @property
    def correct_answer(self):
        """الحصول على الإجابة الصحيحة للسؤال"""
        if self.question_type == 'multiple_choice':
            try:
                return self.options.get(is_correct=True)
            except:
                return None
        elif self.question_type == 'true_false':
            return self.true_false_answer
    
    class Meta:
        ordering = ['id']
        verbose_name = "سؤال"
        verbose_name_plural = "أسئلة"


class QuestionOption(models.Model):
    """نموذج خيارات السؤال (للأسئلة متعددة الخيارات)"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return self.text
    
    class Meta:
        verbose_name = "خيار سؤال"
        verbose_name_plural = "خيارات الأسئلة"


class TrueFalseAnswer(models.Model):
    """نموذج إجابة صح/خطأ"""
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='true_false_answer')
    is_true = models.BooleanField(default=True, help_text="حدد إذا كانت الإجابة الصحيحة هي 'صح'")
    
    def __str__(self):
        return "صح" if self.is_true else "خطأ"
    
    class Meta:
        verbose_name = "إجابة صح/خطأ"
        verbose_name_plural = "إجابات صح/خطأ"


class QuizAttempt(models.Model):
    """نموذج محاولة الاختبار"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    score = models.FloatField(default=0)  # النسبة المئوية
    time_spent = models.PositiveIntegerField(default=0, help_text="الوقت المستغرق بالثواني")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    passed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.score}%"
    
    @property
    def time_spent_formatted(self):
        """تنسيق الوقت المستغرق"""
        minutes = self.time_spent // 60
        seconds = self.time_spent % 60
        return f"{minutes}:{seconds:02d}"
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = "محاولة اختبار"
        verbose_name_plural = "محاولات الاختبارات"


class QuestionResponse(models.Model):
    """نموذج إجابة المستخدم على سؤال"""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    selected_option = models.ForeignKey(QuestionOption, on_delete=models.CASCADE, null=True, blank=True)
    true_false_response = models.BooleanField(null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"إجابة {self.attempt.user.username} على {self.question}"
    
    def save(self, *args, **kwargs):
        # تحديد ما إذا كانت الإجابة صحيحة
        if self.question.question_type == 'multiple_choice' and self.selected_option:
            self.is_correct = self.selected_option.is_correct
        elif self.question.question_type == 'true_false' and self.true_false_response is not None:
            self.is_correct = self.true_false_response == self.question.true_false_answer.is_true
        
        super().save(*args, **kwargs)
    
    class Meta:
        unique_together = ['attempt', 'question']
        verbose_name = "إجابة سؤال"
        verbose_name_plural = "إجابات الأسئلة"

@receiver(post_save, sender=Lesson)
def update_video_duration(sender, instance, **kwargs):
    """تحديث مدة الفيديو تلقائيًا عند حفظ الدرس إذا كان هناك فيديو"""
    if instance.video and instance.duration == 0:
        try:
            # استخدام ffprobe لاستخراج مدة الفيديو
            video_path = instance.video.path
            cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'format=duration', 
                '-of', 'json', 
                video_path
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            data = json.loads(result.stdout)
            duration_seconds = float(data['format']['duration'])
            
            # تحويل الثواني إلى دقائق وتقريبها لأقرب دقيقة
            duration_minutes = round(duration_seconds / 60)
            
            # تحديث مدة الدرس
            if duration_minutes > 0:
                instance.duration = duration_minutes
                # استخدام update لتجنب تشغيل post_save مرة أخرى
                Lesson.objects.filter(pk=instance.pk).update(duration=duration_minutes)
        except Exception as e:
            print(f"خطأ في استخراج مدة الفيديو: {e}")

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'course']
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progress')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    completed = models.BooleanField(default=False)
    last_accessed = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'lesson']
    
    def __str__(self):
        return f"{self.user.username} - {self.lesson.title}"

from django.db import models
from django.contrib.auth.models import User

# نموذج ملف تعريف المستخدم الممتد
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=[('student', 'طالب'), ('instructor', 'معلم')], default='student')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    @property
    def is_instructor(self):
        return self.role == 'instructor'
