from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, Course, Lesson, Quiz, Question, QuestionOption, TrueFalseAnswer , LessonAttachment
from django.conf import settings

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    role = forms.ChoiceField(
        choices=[('student', 'طالب'), ('instructor', 'معلم')],
        widget=forms.RadioSelect,
        initial='student'
    )
    instructor_code = forms.CharField(
        max_length=20, 
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'أدخل كود المعلم'}),
        help_text='مطلوب فقط للتسجيل كمعلم'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'role', 'instructor_code')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تعديل النص التوضيحي للحقول
        self.fields['username'].help_text = 'مطلوب. 150 حرف أو أقل. يمكن استخدام الحروف والأرقام و @/./+/-/_.'
        self.fields['password1'].help_text = 'كلمة المرور يجب أن تكون على الأقل 8 أحرف وغير شائعة.'
        self.fields['password2'].help_text = 'أدخل نفس كلمة المرور للتأكيد.'
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        instructor_code = cleaned_data.get('instructor_code')
        
        # التحقق من كود المعلم إذا تم اختيار دور المعلم
        if role == 'instructor':
            # الحصول على كود المعلم من الإعدادات أو متغيرات البيئة
            valid_instructor_code = getattr(settings, 'INSTRUCTOR_CODE', 'TEACH2023')
            
            if not instructor_code:
                self.add_error('instructor_code', 'كود المعلم مطلوب للتسجيل كمعلم.')
            elif instructor_code != valid_instructor_code:
                self.add_error('instructor_code', 'كود المعلم غير صحيح.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        if commit:
            user.save()
            # إنشاء أو تحديث ملف المستخدم
            role = self.cleaned_data.get('role')
            profile, created = UserProfile.objects.get_or_create(user=user)
            # استخدام حقل role بدلاً من is_instructor
            profile.role = role
            profile.save()
            
        return user

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'image']
        
class LessonForm(forms.ModelForm):
    duration_seconds = forms.IntegerField(
        required=False, 
        min_value=0, 
        max_value=59, 
        initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    video_type = forms.ChoiceField(
        choices=[('file', 'ملف فيديو'), ('youtube', 'رابط يوتيوب')],
        initial='file',
        widget=forms.RadioSelect(attrs={'class': 'video-type-radio'})
    )
    
    video_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.youtube.com/watch?v=...'}),
        help_text="أدخل رابط فيديو يوتيوب"
    )
    
    class Meta:
        model = Lesson
        fields = ['title', 'content', 'video', 'video_url', 'video_type', 'duration', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            total_seconds = self.instance.duration * 60
            self.initial['duration_seconds'] = total_seconds % 60
            self.initial['duration'] = total_seconds // 60
            
            # تعيين نوع الفيديو بناءً على البيانات الموجودة
            if self.instance.video_url:
                self.initial['video_type'] = 'youtube'
            else:
                self.initial['video_type'] = 'file'

    def clean(self):
        cleaned_data = super().clean()
        video_type = cleaned_data.get('video_type')
        video = cleaned_data.get('video')
        video_url = cleaned_data.get('video_url')
        duration = cleaned_data.get('duration') or 0
        duration_seconds = cleaned_data.get('duration_seconds') or 0
        
        # التحقق من وجود فيديو أو رابط يوتيوب حسب النوع المحدد
        if video_type == 'file' and not (video or self.instance and self.instance.video):
            if not self.files.get('video'):
                self.add_error('video', 'يرجى تحميل ملف فيديو')
        elif video_type == 'youtube' and not video_url:
            self.add_error('video_url', 'يرجى إدخال رابط فيديو يوتيوب')
        
        # التحقق من صحة رابط يوتيوب
        if video_type == 'youtube' and video_url:
            import re
            youtube_regex = (
                r'(https?://)?(www\.)?'
                r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
                r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
            
            match = re.match(youtube_regex, video_url)
            if not match:
                self.add_error('video_url', 'رابط يوتيوب غير صالح')
        
        # حساب المدة الإجمالية بالثواني
        total_seconds = (duration * 60) + duration_seconds
        cleaned_data['duration'] = total_seconds // 60
        
        return cleaned_data


class LessonAttachmentForm(forms.ModelForm):
    class Meta:
        model = LessonAttachment
        fields = ['attachment_file']
        labels = {
            'attachment_file': 'الملف المرفق',
        }
        help_texts = {
            'attachment_file': 'الملفات المدعومة: PDF, PPTX, DOCX, ZIP, RAR',
        }


LessonAttachmentFormSet = forms.inlineformset_factory(
    Lesson, 
    LessonAttachment,
    form=LessonAttachmentForm,
    extra=1,
    can_delete=True
)

class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)
    bio = forms.CharField(widget=forms.Textarea, required=False)
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'bio']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # تحديث بيانات المستخدم
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            profile.save()
        
        return profile

# إضافة نماذج الاختبارات الجديدة

class QuizForm(forms.ModelForm):
    """نموذج إنشاء اختبار جديد"""
    class Meta:
        model = Quiz
        fields = ['title', 'description', 'time_limit', 'passing_score']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'time_limit': forms.NumberInput(attrs={'min': 1, 'max': 180}),
            'passing_score': forms.NumberInput(attrs={'min': 1, 'max': 100}),
        }
        labels = {
            'title': 'عنوان الاختبار',
            'description': 'وصف الاختبار',
            'time_limit': 'مدة الاختبار (بالدقائق)',
            'passing_score': 'درجة النجاح (%)',
        }
        help_texts = {
            'time_limit': 'حدد مدة الاختبار بالدقائق (من 1 إلى 180 دقيقة)',
            'passing_score': 'النسبة المئوية المطلوبة للنجاح في الاختبار',
        }

class QuestionForm(forms.ModelForm):
    """نموذج إنشاء سؤال جديد"""
    class Meta:
        model = Question
        fields = ['text', 'question_type']
        labels = {
            'text': 'نص السؤال',
            'question_type': 'نوع السؤال',
        }

class QuestionOptionForm(forms.ModelForm):
    """نموذج خيارات السؤال"""
    class Meta:
        model = QuestionOption
        fields = ['text', 'is_correct']
        labels = {
            'text': 'نص الخيار',
            'is_correct': 'إجابة صحيحة',
        }

class TrueFalseAnswerForm(forms.ModelForm):
    """نموذج إجابة صح/خطأ"""
    class Meta:
        model = TrueFalseAnswer
        fields = ['is_true']
        labels = {
            'is_true': 'الإجابة الصحيحة هي "صح"',
        }

# نموذج مساعد لإنشاء اختبار كامل مع أسئلته
class CreateQuizForm(forms.Form):
    """نموذج إنشاء اختبار كامل مع أسئلته"""
    title = forms.CharField(max_length=200, label='عنوان الاختبار')
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label='وصف الاختبار')
    time_limit = forms.IntegerField(min_value=1, max_value=180, initial=30, label='مدة الاختبار (بالدقائق)')
    passing_score = forms.IntegerField(min_value=1, max_value=100, initial=60, label='درجة النجاح (%)')
    
    # حقول ديناميكية للأسئلة ستتم إضافتها في العرض (view)