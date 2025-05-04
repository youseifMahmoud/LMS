from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.utils import timezone
from .models import Course, Lesson, Enrollment, LessonProgress, UserProfile , Rating, LessonAttachment
import json
import os
import re
from django.conf import settings
import requests
from django.http import JsonResponse
from .forms import CourseForm, LessonForm, ProfileEditForm, LessonAttachmentForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Avg
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .models import Course, Quiz, Question, QuestionOption, TrueFalseAnswer, QuizAttempt, QuestionResponse , LessonAttachment
from django.contrib import messages
from django.db import transaction
from django.urls import reverse

def home(request):
    featured_courses = Course.objects.all()[:3]
    
    # حساب وتحضير بيانات المدة لكل دورة
    for course in featured_courses:
        # حساب إجمالي مدة الدورة من جميع الدروس
        total_minutes = 0
        for lesson in course.lessons.all():
            if hasattr(lesson, 'duration') and lesson.duration:
                total_minutes += lesson.duration
        
        # تخزين المدة الإجمالية
        course.total_duration = total_minutes
        
        # تحويل المدة إلى ساعات ودقائق
        course.duration_hours = total_minutes // 60
        course.duration_minutes = total_minutes % 60
    
    return render(request, 'courses/home.html', {
        'featured_courses': featured_courses
    })

class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 9
    ordering = ['-id']  
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # حساب وتحضير بيانات المدة لكل دورة
        for course in context['courses']:
            # حساب إجمالي مدة الدورة من جميع الدروس
            total_minutes = 0
            for lesson in course.lessons.all():
                if hasattr(lesson, 'duration') and lesson.duration:
                    total_minutes += lesson.duration
            
            # تخزين المدة الإجمالية
            course.total_duration = total_minutes
            
            # تحويل المدة إلى ساعات ودقائق
            course.duration_hours = total_minutes // 60
            course.duration_minutes = total_minutes % 60
        
        return context

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    is_enrolled = False
    is_instructor = False
    course_completed = False
    completed_lessons_count = 0
    passed_quizzes = []
    progress_percentage = 0
    progress_text = ""
    
    if request.user.is_authenticated:
        # التحقق مما إذا كان المستخدم هو معلم الدورة
        is_instructor = course.instructor == request.user
        
        # التحقق من تسجيل المستخدم في الدورة
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        is_enrolled = enrollment is not None
        
        # حساب عدد الدروس المكتملة والاختبارات المجتازة
        if is_enrolled:
            # الدروس المكتملة
            completed_lessons = LessonProgress.objects.filter(
                user=request.user,
                lesson__course=course,
                completed=True
            )
            completed_lessons_count = completed_lessons.count()
            
            # الاختبارات المجتازة
            passed_quiz_attempts = QuizAttempt.objects.filter(
                user=request.user,
                quiz__course=course,
                passed=True
            ).values_list('quiz_id', flat=True)
            passed_quizzes = list(passed_quiz_attempts)
            
            # حساب نسبة التقدم في الدورة (الدروس + الاختبارات)
            total_items = course.lessons.count() + course.quizzes.count()
            completed_items = completed_lessons_count + len(passed_quizzes)
            
            if total_items > 0:
                progress_percentage = int((completed_items / total_items) * 100)
                progress_text = f"{completed_items} من {total_items} مكتمل"
                
                # التحقق مما إذا كانت الدورة مكتملة
                course_completed = (progress_percentage == 100)
            else:
                progress_percentage = 0
                progress_text = "لا توجد عناصر للإكمال"
    
    # حساب إجمالي مدة الدورة من جميع الدروس
    total_minutes = 0
    total_seconds = 0
    for lesson in course.lessons.all():
        if hasattr(lesson, 'duration') and lesson.duration:
            total_minutes += lesson.duration
        if hasattr(lesson, 'duration_seconds') and lesson.duration_seconds:
            total_seconds += lesson.duration_seconds
    
    # تحويل الثواني الزائدة إلى دقائق
    additional_minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    
    # تخزين المدة الإجمالية
    course.total_duration = total_minutes + additional_minutes
    course.total_seconds = remaining_seconds
    
    # تحويل المدة إلى ساعات ودقائق وثواني
    total_minutes_with_overflow = total_minutes + additional_minutes
    course.duration_hours = total_minutes_with_overflow // 60
    course.duration_minutes = total_minutes_with_overflow % 60
    course.duration_seconds = remaining_seconds
    
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'is_enrolled': is_enrolled,
        'is_instructor': is_instructor,
        'course_completed': course_completed,
        'completed_lessons_count': completed_lessons_count,
        'passed_quizzes': passed_quizzes,
        'progress_percentage': progress_percentage,
        'progress_text': progress_text
    })


@login_required
def enroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    
    # Check if already enrolled
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, 'You are already enrolled in this course.')
        return redirect('course_detail', pk=course.id)
    
    # Create enrollment
    enrollment = Enrollment.objects.create(user=request.user, course=course)
    messages.success(request, f'You have successfully enrolled in {course.title}.')
    
    # Redirect to the first lesson if available
    first_lesson = course.lessons.first()
    if first_lesson:
        return redirect('lesson_detail', course_id=course.id, lesson_id=first_lesson.id)
    
    return redirect('course_detail', pk=course.id)

@login_required
def lesson_detail(request, course_id, lesson_id):
    course = get_object_or_404(Course, pk=course_id)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    
    # التحقق مما إذا كان المستخدم هو معلم الدورة
    is_instructor = course.instructor == request.user
    
    if is_instructor:
        # المعلم يمكنه الوصول إلى الدرس دون الحاجة للتسجيل في الدورة
        enrollment = None
    else:
        # التحقق من تسجيل المستخدم في الدورة
        enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
    
    # الحصول على تقدم الدرس
    if not is_instructor:
        lesson_completed, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={'completed': False}
        )
        
        # الحصول على الدروس المكتملة
        completed_lessons = LessonProgress.objects.filter(
            user=request.user,
            lesson__course=course,
            completed=True
        ).values_list('lesson_id', flat=True)
        
        # حساب التقدم
        total_lessons = course.lessons.count()
        completed_count = len(completed_lessons)
        progress = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0
    else:
        # للمعلم، لا نحتاج لحساب التقدم
        lesson_completed = False
        completed_lessons = []
        progress = 0
        completed_count = 0
        total_lessons = course.lessons.count()
    
    # الحصول على الدروس السابقة والتالية
    lessons = list(course.lessons.order_by('order'))
    current_index = lessons.index(lesson)
    prev_lesson = lessons[current_index - 1] if current_index > 0 else None
    next_lesson = lessons[current_index + 1] if current_index < len(lessons) - 1 else None
    
    return render(request, 'courses/lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'lesson_completed': lesson_completed.completed if not is_instructor else False,
        'completed_lessons': completed_lessons,
        'progress': progress,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'is_instructor': is_instructor,  # إضافة متغير للتحقق من كون المستخدم معلماً
        'completed_count': completed_count,
        'total_lessons': total_lessons
    })

@login_required
def complete_lesson(request, course_id, lesson_id):
    if request.method == 'POST':
        course = get_object_or_404(Course, pk=course_id)
        lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
        
        # Mark lesson as complete
        progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={'completed': True}
        )
        
        if not created and not progress.completed:
            progress.completed = True
            progress.save()
        
        # Check if all lessons are completed
        total_lessons = course.lessons.count()
        completed_lessons = LessonProgress.objects.filter(
            user=request.user,
            lesson__course=course,
            completed=True
        ).count()
        
        # If all lessons completed, mark enrollment as completed
        if total_lessons == completed_lessons:
            enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
            enrollment.completed = True
            enrollment.completed_date = timezone.now()
            enrollment.save()
            messages.success(request, f'Congratulations! You have completed the course "{course.title}".')
        else:
            messages.success(request, 'Lesson marked as complete.')
        
        # Redirect to next lesson if available
        lessons = list(course.lessons.order_by('order'))
        current_index = lessons.index(lesson)
        if current_index < len(lessons) - 1:
            next_lesson = lessons[current_index + 1]
            return redirect('lesson_detail', course_id=course.id, lesson_id=next_lesson.id)
    
    return redirect('lesson_detail', course_id=course_id, lesson_id=lesson_id)

@login_required
def certificate(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id, user=request.user, completed=True)
    
    return render(request, 'courses/certificate.html', {
        'enrollment': enrollment
    })

def is_instructor(user):
    try:
        return user.profile.is_instructor
    except UserProfile.DoesNotExist:
        return False


@login_required
def dashboard(request):
    user = request.user
    active_tab = request.GET.get('tab', 'in_progress')
    
    if is_instructor(user):
        # المعلم - عرض الدورات التي يقوم بتدريسها
        instructor_courses = Course.objects.filter(instructor=user)
        
        # إضافة معلومات إضافية لكل دورة
        courses_data = []
        for course in instructor_courses:
            # حساب متوسط التقييم لكل دورة
            avg_rating = course.ratings.aggregate(avg=Avg('rating'))['avg']  # استخدم Avg مباشرة
            avg_rating = round(avg_rating, 1) if avg_rating else 0
            
            course_data = {
                'course': course,
                'total_students': Enrollment.objects.filter(course=course).count(),
                'total_lessons': course.lessons.count(),
                'average_rating': avg_rating,
                'total_ratings': course.ratings.count(),
            }
            courses_data.append(course_data)
        
        # حساب متوسط التقييم الإجمالي لجميع دورات المعلم
        all_ratings = Rating.objects.filter(course__instructor=user)
        overall_rating = all_ratings.aggregate(avg=Avg('rating'))['avg']  # استخدم Avg مباشرة
        overall_rating = round(overall_rating, 1) if overall_rating else 0
        
        return render(request, 'courses/dashboard.html', {
            'instructor_courses': instructor_courses,
            'courses_data': courses_data,
            'instructor_courses_count': instructor_courses.count(),
            'total_students': Enrollment.objects.filter(course__instructor=user).count(),
            'average_rating': overall_rating,
            'is_instructor': True
        })
    else:
        # الطالب - عرض الدورات المسجل فيها
        enrollments = Enrollment.objects.filter(user=user).select_related('course')
        
        in_progress_enrollments = []
        completed_enrollments = []
        
        # تحديد حالة كل تسجيل (مكتمل أو قيد التقدم)
        for enrollment in enrollments:
            course = enrollment.course
            total_lessons = course.lessons.count()
            total_quizzes = course.quizzes.count()
            
            if total_lessons > 0:
                # حساب عدد الدروس المكتملة
                completed_lessons = LessonProgress.objects.filter(
                    user=user,
                    lesson__course=course,
                    completed=True
                ).count()
                
                # حساب عدد الاختبارات المجتازة
                passed_quizzes = QuizAttempt.objects.filter(
                    user=user,
                    quiz__course=course,
                    passed=True
                ).count()
                
                # حساب نسبة التقدم (الدروس + الاختبارات)
                total_items = total_lessons + total_quizzes
                completed_items = completed_lessons + passed_quizzes
                
                if total_items > 0:
                    enrollment.progress = int((completed_items / total_items) * 100)
                else:
                    enrollment.progress = 0
                
                # تحديد ما إذا كانت الدورة مكتملة
                # الدورة تعتبر مكتملة فقط إذا:
                # 1. تم إكمال جميع الدروس
                # 2. تم اجتياز جميع الاختبارات (إذا كانت موجودة)
                is_completed = False
                if completed_lessons == total_lessons:  # تم إكمال جميع الدروس
                    if total_quizzes == 0 or passed_quizzes == total_quizzes:  # لا توجد اختبارات أو تم اجتياز جميع الاختبارات
                        is_completed = True
                
                # تحديث حالة التسجيل
                if is_completed:
                    # إذا كانت الدورة مكتملة سابقًا ولكن تمت إضافة دروس جديدة
                    if enrollment.completed and completed_lessons < total_lessons:
                        enrollment.completed = False
                        enrollment.save()
                        in_progress_enrollments.append(enrollment)
                    else:
                        # تحديث حالة الإكمال إذا لم تكن محدثة بالفعل
                        if not enrollment.completed:
                            enrollment.completed = True
                            enrollment.completed_date = timezone.now()
                            enrollment.save()
                        completed_enrollments.append(enrollment)
                else:
                    # إذا كانت الدورة مكتملة سابقًا ولكن لم تعد كذلك
                    if enrollment.completed:
                        enrollment.completed = False
                        enrollment.save()
                    in_progress_enrollments.append(enrollment)
            else:
                # إذا لم تكن هناك دروس، فالدورة تعتبر قيد التقدم
                if enrollment.completed:
                    enrollment.completed = False
                    enrollment.save()
                in_progress_enrollments.append(enrollment)
                enrollment.progress = 0
        
        # حساب إجمالي وقت التعلم
        total_learning_minutes = 0
        
        # جمع جميع الدورات التي سجل فيها المستخدم (قيد التقدم والمكتملة)
        all_enrollments = in_progress_enrollments + completed_enrollments
        
        # حساب إجمالي وقت التعلم من جميع الدروس في جميع الدورات المسجل فيها
        for enrollment in all_enrollments:
            # الحصول على جميع الدروس في الدورة
            lessons = enrollment.course.lessons.all()
            for lesson in lessons:
                # إضافة مدة الدرس إلى إجمالي الوقت
                if hasattr(lesson, 'duration') and lesson.duration:
                    total_learning_minutes += lesson.duration
        
        # تحويل الدقائق إلى ساعات ودقائق
        total_hours = total_learning_minutes // 60
        total_minutes = total_learning_minutes % 60
        
        return render(request, 'courses/dashboard.html', {
            'in_progress_enrollments': in_progress_enrollments,
            'completed_enrollments': completed_enrollments,
            'in_progress_count': len(in_progress_enrollments),
            'completed_count': len(completed_enrollments),
            'total_hours': total_hours,
            'total_minutes': total_minutes,
            'active_tab': active_tab,
            'is_instructor': False
        })
    
@login_required
def rate_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # التحقق من أن المستخدم مسجل في الدورة
    if not Enrollment.objects.filter(course=course, user=request.user).exists():
        messages.error(request, 'يجب أن تكون مسجلاً في الدورة لتقييمها.')
        return redirect('course_detail', pk=course.id)  # تغيير من course_id إلى pk
    
    if request.method == 'POST':
        rating_value = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        if not rating_value:
            messages.error(request, 'يرجى اختيار تقييم.')
            return redirect('course_detail', pk=course.id)  # تغيير من course_id إلى pk
        
        # إنشاء أو تحديث التقييم
        rating, created = Rating.objects.update_or_create(
            course=course,
            user=request.user,
            defaults={
                'rating': rating_value,
                'comment': comment
            }
        )
        
        messages.success(request, 'تم حفظ تقييمك بنجاح.')
        return redirect('course_detail', pk=course.id)  # تغيير من course_id إلى pk
    
    # إذا كان المستخدم قد قام بالتقييم من قبل، استرجع التقييم الحالي
    try:
        user_rating = Rating.objects.get(course=course, user=request.user)
    except Rating.DoesNotExist:
        user_rating = None
    
    context = {
        'course': course,
        'user_rating': user_rating
    }
    
    return render(request, 'courses/rate_course.html', context)

@login_required
@user_passes_test(is_instructor)
def create_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            messages.success(request, 'تم إنشاء الدورة بنجاح.')
            return redirect('edit_course', pk=course.id)
    else:
        form = CourseForm()
    
    return render(request, 'courses/create_course.html', {
        'form': form
    })

@login_required
@user_passes_test(is_instructor)
def edit_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الدورة بنجاح.')
            return redirect('edit_course', pk=course.id)
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'courses/edit_course.html', {
        'form': form,
        'course': course
    })

@login_required
@user_passes_test(is_instructor)
def create_quiz(request, course_id):
    """عرض إنشاء اختبار جديد"""
    course = get_object_or_404(Course, id=course_id)
    
    # التحقق من أن المستخدم هو مالك الدورة
    if course.instructor != request.user:
        return redirect('course_detail', course_id=course_id)
    
    if request.method == 'POST':
        # التحقق مما إذا كان الطلب هو طلب AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            # استخراج بيانات النموذج
            data = request.POST
            
            # طباعة بيانات النموذج للتصحيح
            print("=" * 50)
            print("POST data:")
            for key, value in data.items():
                print(f"{key}: {value}")
            print("=" * 50)
            
            # إنشاء الاختبار
            with transaction.atomic():
                quiz = Quiz.objects.create(
                    course=course,
                    title=data.get('title'),
                    description=data.get('description', ''),
                    time_limit=int(data.get('time_limit', 30)),
                    passing_score=int(data.get('passing_score', 60))
                )
                
                # استخراج بيانات الأسئلة
                question_texts = data.getlist('question_text[]')
                
                # إنشاء الأسئلة - جميع الأسئلة الآن من نوع اختيار متعدد
                for i in range(len(question_texts)):
                    if question_texts[i].strip():
                        question = Question.objects.create(
                            quiz=quiz,
                            text=question_texts[i],
                            question_type='multiple_choice'  # دائمًا اختيار متعدد
                        )
                        
                        # استخراج خيارات السؤال
                        option_texts = []
                        
                        # البحث عن جميع المفاتيح التي تطابق النمط option_text_{i}_*
                        for key, value in data.items():
                            # استخدام تعبير منتظم للعثور على الخيارات المناسبة
                            option_text_match = re.match(rf'option_text_{i}_(\d+)', key)
                            
                            if option_text_match:
                                option_index = int(option_text_match.group(1))
                                # تأكد من أن لدينا مساحة كافية في القائمة
                                while len(option_texts) <= option_index:
                                    option_texts.append(None)
                                option_texts[option_index] = value
                        
                        # استخدام الطريقة القديمة كاحتياط
                        if not option_texts:
                            option_texts = data.getlist(f'option_text_{i}[]')
                        
                        correct_answer = data.get(f'correct_answer_{i}')
                        
                        print(f"Question {i+1} (ID: {question.id}) options: {option_texts}")
                        print(f"Question {i+1} (ID: {question.id}) correct answer: {correct_answer}")
                        
                        if correct_answer is not None:
                            correct_index = int(correct_answer)
                            
                            for j, option_text in enumerate(option_texts):
                                if option_text and option_text.strip():
                                    QuestionOption.objects.create(
                                        question=question,
                                        text=option_text,
                                        is_correct=(j == correct_index)
                                    )
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'redirect_url': f'/courses/{course_id}/edit/'
                })
            else:
                return redirect('edit_course', course_id=course_id)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
            else:
                # يمكنك إضافة رسالة خطأ هنا باستخدام messages framework
                return render(request, 'courses/create_quiz.html', {
                    'course': course,
                    'error': str(e)
                })
    
    # عرض نموذج إنشاء اختبار جديد
    return render(request, 'courses/create_quiz.html', {
        'course': course
    })

@login_required
@user_passes_test(is_instructor)
def edit_quiz(request, course_id, quiz_id):
    """تعديل اختبار موجود"""
    course = get_object_or_404(Course, pk=course_id, instructor=request.user)
    quiz = get_object_or_404(Quiz, pk=quiz_id, course=course)
    
    if request.method == 'POST':
        try:
            # طباعة بيانات النموذج للتصحيح
            print("=" * 50)
            print("POST data:")
            for key, value in request.POST.items():
                print(f"{key}: {value}")
            print("=" * 50)
            
            # استخراج بيانات الاختبار الأساسية
            title = request.POST.get('title')
            description = request.POST.get('description')
            time_limit = request.POST.get('time_limit')
            passing_score = request.POST.get('passing_score')
            
            # التحقق من البيانات
            if not title or not time_limit or not passing_score:
                messages.error(request, 'يرجى ملء جميع الحقول المطلوبة')
                return redirect('edit_quiz', course_id=course.id, quiz_id=quiz.id)
            
            # تحديث الاختبار
            with transaction.atomic():
                quiz.title = title
                quiz.description = description
                quiz.time_limit = time_limit
                quiz.passing_score = passing_score
                quiz.save()
                
                # استخراج بيانات الأسئلة
                question_ids = request.POST.getlist('question_id[]', [])
                question_texts = request.POST.getlist('question_text[]', [])
                
                print(f"Found {len(question_ids)} questions")
                
                # التحقق من وجود أسئلة
                if not question_texts:
                    messages.error(request, 'يجب إضافة سؤال واحد على الأقل')
                    return redirect('edit_quiz', course_id=course.id, quiz_id=quiz.id)
                
                # حذف الأسئلة القديمة التي لم تعد موجودة
                existing_question_ids = [qid for qid in question_ids if qid and qid != 'new']
                if existing_question_ids:
                    existing_question_ids = [int(qid) for qid in existing_question_ids]
                    deleted_questions = quiz.questions.exclude(id__in=existing_question_ids).delete()
                    print(f"Deleted questions not in {existing_question_ids}: {deleted_questions}")
                
                # تحديث أو إنشاء الأسئلة
                for i, (q_id, text) in enumerate(zip(question_ids, question_texts)):
                    print(f"\nProcessing question {i+1}: ID={q_id}, Text={text}")
                    
                    # التحقق مما إذا كان السؤال موجودًا بالفعل
                    if q_id and q_id != 'new':
                        # تحديث سؤال موجود
                        question = get_object_or_404(Question, pk=q_id, quiz=quiz)
                        old_type = question.question_type
                        question.text = text
                        question.question_type = 'multiple_choice'  # تحويل جميع الأسئلة إلى اختيار متعدد
                        question.save()
                        
                        print(f"Updated question {question.id}: old_type={old_type}, new_type=multiple_choice")
                        
                        # حذف إجابات صح/خطأ إذا كان السؤال من هذا النوع سابقًا
                        if old_type == 'true_false':
                            tf_deleted = TrueFalseAnswer.objects.filter(question=question).delete()
                            print(f"Deleted TF answers for question {question.id}: {tf_deleted}")
                    else:
                        # إنشاء سؤال جديد
                        question = Question.objects.create(
                            quiz=quiz,
                            text=text,
                            question_type='multiple_choice'  # دائمًا اختيار متعدد
                        )
                        print(f"Created new question {question.id} with type multiple_choice")
                    
                    # استخراج خيارات السؤال
                    option_texts = []
                    option_ids = []
                    
                    # البحث عن جميع المفاتيح التي تطابق النمط option_text_{i}_*
                    for key, value in request.POST.items():
                        # استخدام تعبير منتظم للعثور على الخيارات المناسبة
                        option_text_match = re.match(rf'option_text_{i}_(\d+)', key)
                        option_id_match = re.match(rf'option_id_{i}_(\d+)', key)
                        
                        # أيضًا البحث عن النمط القديم option_text_{i}[{j}]
                        if not option_text_match:
                            old_pattern_match = re.match(rf'option_text_{i}\[(\d+)\]', key)
                            if old_pattern_match:
                                option_index = int(old_pattern_match.group(1))
                                while len(option_texts) <= option_index:
                                    option_texts.append(None)
                                option_texts[option_index] = value
                        else:
                            option_index = int(option_text_match.group(1))
                            # تأكد من أن لدينا مساحة كافية في القائمة
                            while len(option_texts) <= option_index:
                                option_texts.append(None)
                            option_texts[option_index] = value
                        
                        # أيضًا البحث عن النمط القديم option_id_{i}[{j}]
                        if not option_id_match:
                            old_id_pattern_match = re.match(rf'option_id_{i}\[(\d+)\]', key)
                            if old_id_pattern_match:
                                option_index = int(old_id_pattern_match.group(1))
                                while len(option_ids) <= option_index:
                                    option_ids.append(None)
                                option_ids[option_index] = value
                        else:
                            option_index = int(option_id_match.group(1))
                            # تأكد من أن لدينا مساحة كافية في القائمة
                            while len(option_ids) <= option_index:
                                option_ids.append(None)
                            option_ids[option_index] = value
                    
                    correct_answer = request.POST.get(f'correct_answer_{i}')
                    
                    print(f"Question {i+1} (ID: {question.id}) options: {option_texts}")
                    print(f"Question {i+1} (ID: {question.id}) correct answer: {correct_answer}")
                    
                    # تعيين قيمة افتراضية للإجابة الصحيحة إذا كانت فارغة
                    if correct_answer is None or correct_answer == '':
                        correct_answer = '0'
                        print(f"Using default correct answer '0' for question {question.id}")
                    
                    # حذف الخيارات القديمة التي لم تعد موجودة
                    if option_ids:
                        existing_option_ids = [oid for oid in option_ids if oid]
                        if existing_option_ids:
                            existing_option_ids = [int(oid) for oid in existing_option_ids if oid]
                            if existing_option_ids:
                                deleted_options = question.options.exclude(id__in=existing_option_ids).delete()
                                print(f"Deleted options not in {existing_option_ids}: {deleted_options}")
                    
                    # تحديث أو إنشاء خيارات السؤال
                    for j, opt_text in enumerate(option_texts):
                        if opt_text is None:
                            continue
                            
                        is_correct = (str(j) == str(correct_answer))
                        
                        # الحصول على معرف الخيار إذا كان موجودًا
                        option_id = None
                        if j < len(option_ids) and option_ids[j]:
                            option_id = option_ids[j]
                        
                        if option_id:
                            # تحديث خيار موجود
                            try:
                                option = QuestionOption.objects.get(pk=option_id, question=question)
                                option.text = opt_text
                                option.is_correct = is_correct
                                option.save()
                                print(f"Updated option {option.id} for question {question.id}: {opt_text}, is_correct={is_correct}")
                            except QuestionOption.DoesNotExist:
                                # إنشاء خيار جديد إذا لم يكن موجودًا
                                option = QuestionOption.objects.create(
                                    question=question,
                                    text=opt_text,
                                    is_correct=is_correct
                                )
                                print(f"Created new option {option.id} for question {question.id}: {opt_text}, is_correct={is_correct}")
                        else:
                            # إنشاء خيار جديد
                            option = QuestionOption.objects.create(
                                question=question,
                                text=opt_text,
                                is_correct=is_correct
                            )
                            print(f"Created new option {option.id} for question {question.id}: {opt_text}, is_correct={is_correct}")
                
                messages.success(request, 'تم تحديث الاختبار بنجاح')
                return redirect('edit_course', pk=course.id)
                
        except Exception as e:
            # تسجيل الخطأ وإظهار رسالة للمستخدم
            print(f"Error saving quiz: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'حدث خطأ أثناء حفظ الاختبار: {str(e)}')
            return redirect('edit_quiz', course_id=course.id, quiz_id=quiz.id)
    
    return render(request, 'courses/edit_quiz.html', {
        'course': course,
        'quiz': quiz
    })


@login_required
@user_passes_test(is_instructor)
def delete_quiz(request, course_id, quiz_id):
    """حذف اختبار"""
    course = get_object_or_404(Course, pk=course_id, instructor=request.user)
    quiz = get_object_or_404(Quiz, pk=quiz_id, course=course)
    
    if request.method == 'POST':
        quiz.delete()
        messages.success(request, 'تم حذف الاختبار بنجاح')
    
    return redirect('edit_course', pk=course.id)

@login_required
def take_quiz(request, course_id, quiz_id):
    """صفحة إجراء الاختبار"""
    course = get_object_or_404(Course, pk=course_id)
    quiz = get_object_or_404(Quiz, pk=quiz_id, course=course)
    
    # التحقق من تسجيل المستخدم في الدورة
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
    
    # التحقق من عدم وجود محاولة سابقة مكتملة (إذا كنت تريد السماح بمحاولة واحدة فقط)
    # previous_attempt = QuizAttempt.objects.filter(user=request.user, quiz=quiz, is_completed=True).exists()
    # if previous_attempt:
    #     messages.info(request, 'لقد أكملت هذا الاختبار بالفعل')
    #     return redirect('course_detail', pk=course.id)
    
    # إنشاء محاولة جديدة أو استخدام محاولة غير مكتملة
    attempt, created = QuizAttempt.objects.get_or_create(
        user=request.user,
        quiz=quiz,
        is_completed=False,
        defaults={'started_at': timezone.now()}
    )
    
    return render(request, 'courses/take_quiz.html', {
        'course': course,
        'quiz': quiz,
        'attempt': attempt
    })

@login_required
def submit_quiz(request, course_id, quiz_id):
    """معالجة إرسال إجابات الاختبار"""
    if request.method != 'POST':
        return redirect('course_detail', pk=course_id)
    
    course = get_object_or_404(Course, pk=course_id)
    quiz = get_object_or_404(Quiz, pk=quiz_id, course=course)
    
    # الحصول على المحاولة الحالية أو إنشاء واحدة جديدة
    attempt, created = QuizAttempt.objects.get_or_create(
        user=request.user,
        quiz=quiz,
        is_completed=False,
        defaults={'started_at': timezone.now()}
    )
    
    # تحديث وقت الإكمال والوقت المستغرق
    attempt.is_completed = True
    attempt.completed_at = timezone.now()
    attempt.time_spent = int(request.POST.get('time_spent', 0))
    
    # حفظ إجابات المستخدم
    correct_count = 0
    total_questions = quiz.questions.count()
    
    with transaction.atomic():
        for question in quiz.questions.all():
            answer_key = f'answer_{question.id}'
            user_answer = request.POST.get(answer_key)
            
            if question.question_type == 'multiple_choice':
                # الإجابة هي معرف الخيار المحدد
                if user_answer:
                    selected_option = get_object_or_404(QuestionOption, pk=user_answer)
                    response = QuestionResponse.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_option=selected_option
                    )
                    if selected_option.is_correct:
                        correct_count += 1
            
            elif question.question_type == 'true_false':
                # الإجابة هي 'true' أو 'false'
                if user_answer:
                    true_false_value = (user_answer == 'true')
                    response = QuestionResponse.objects.create(
                        attempt=attempt,
                        question=question,
                        true_false_response=true_false_value
                    )
                    if true_false_value == question.true_false_answer.is_true:
                        correct_count += 1
    
    # حساب النتيجة
    if total_questions > 0:
        score = (correct_count / total_questions) * 100
    else:
        score = 0
    
    attempt.score = score
    attempt.passed = score >= quiz.passing_score
    attempt.save()
    
    # توجيه المستخدم إلى صفحة النتائج
    return redirect('quiz_results', course_id=course.id, quiz_id=quiz.id, attempt_id=attempt.id)

@login_required
def quiz_results(request, course_id, quiz_id, attempt_id):
    """عرض نتائج الاختبار"""
    course = get_object_or_404(Course, pk=course_id)
    quiz = get_object_or_404(Quiz, pk=quiz_id, course=course)
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id, user=request.user, quiz=quiz)
    
    # تحضير بيانات الأسئلة والإجابات للعرض
    questions_data = []
    
    for question in quiz.questions.all():
        question_data = {
            'id': question.id,
            'text': question.text,
            'question_type': question.question_type,
        }
        
        # الحصول على إجابة المستخدم
        try:
            response = attempt.responses.get(question=question)
            if question.question_type == 'multiple_choice':
                question_data['user_answer'] = response.selected_option.id if response.selected_option else None
                question_data['correct_answer'] = question.correct_answer.id if question.correct_answer else None
                question_data['options'] = [{
                    'id': option.id,
                    'text': option.text,
                    'is_correct': option.is_correct
                } for option in question.options.all()]
            else:  # true_false
                question_data['user_answer'] = 'true' if response.true_false_response else 'false'
                question_data['correct_answer'] = 'true' if question.true_false_answer.is_true else 'false'
            
            question_data['is_correct'] = response.is_correct
        except QuestionResponse.DoesNotExist:
            # لم يجب المستخدم على هذا السؤال
            question_data['user_answer'] = None
            question_data['is_correct'] = False
            if question.question_type == 'multiple_choice':
                question_data['correct_answer'] = question.correct_answer.id if question.correct_answer else None
                question_data['options'] = [{
                    'id': option.id,
                    'text': option.text,
                    'is_correct': option.is_correct
                } for option in question.options.all()]
            else:  # true_false
                question_data['correct_answer'] = 'true' if question.true_false_answer.is_true else 'false'
        
        questions_data.append(question_data)
    
    # حساب الوقت المستغرق بتنسيق دقائق:ثواني
    minutes = attempt.time_spent // 60
    seconds = attempt.time_spent % 60
    
    context = {
        'course': course,
        'quiz': quiz,
        'attempt': attempt,
        'questions': questions_data,
        'correct_answers': sum(1 for q in questions_data if q['is_correct']),
        'total_questions': len(questions_data),
        'score': round(attempt.score, 1),
        'passed': attempt.passed,
        'time_spent_minutes': minutes,
        'time_spent_seconds': f"{seconds:02d}"
    }
    
    return render(request, 'courses/quiz_results.html', context)

@login_required
@user_passes_test(is_instructor)
def delete_course(request, pk):
    course = get_object_or_404(Course, pk=pk, instructor=request.user)
    
    if request.method == 'POST':
        # حذف الصورة والملفات المرتبطة بالكورس
        if course.image:
            course.image.delete()
        
        # حذف الفيديوهات المرتبطة بالدروس
        for lesson in course.lessons.all():
            if lesson.video:
                lesson.video.delete()
        
        # حذف الكورس
        course.delete()
        messages.success(request, 'تم حذف الدورة بنجاح.')
        return redirect('dashboard')
    
    return redirect('dashboard')


@login_required
@user_passes_test(is_instructor)
def create_lesson(request, course_id):
    course = get_object_or_404(Course, pk=course_id, instructor=request.user)
    next_order = course.lessons.count() + 1
    
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        
        if form.is_valid():
            # حفظ الدرس
            lesson = form.save(commit=False)
            lesson.course = course
            
            # معالجة نوع الفيديو
            video_type = form.cleaned_data.get('video_type')
            if video_type == 'youtube':
                # إذا كان نوع الفيديو يوتيوب، نحذف أي ملف فيديو موجود
                lesson.video = None
                lesson.video_type = 'youtube'
            else:
                # إذا كان نوع الفيديو ملف، نحذف أي رابط يوتيوب موجود
                lesson.video_url = None
                lesson.video_type = 'file'
            
            # حفظ المدة بالثواني
            lesson.duration_seconds = form.cleaned_data.get('duration_seconds', 0)
            
            lesson.save()
            
            # معالجة الملفات المرفقة
            for file in request.FILES.getlist('attachment_files'):
                # استخراج اسم الملف بدون الامتداد
                filename = os.path.splitext(file.name)[0]
                
                # إنشاء مرفق جديد
                attachment = LessonAttachment(
                    lesson=lesson,
                    attachment_file=file,
                    filename=filename
                )
                attachment.save()
            
            messages.success(request, 'تم إضافة الدرس بنجاح.')
            return redirect('edit_course', pk=course.id)
    else:
        form = LessonForm(initial={'order': next_order, 'duration': 0, 'duration_seconds': 0})
    
    return render(request, 'courses/create_lesson.html', {
        'form': form,
        'course': course,
        'next_order': next_order
    })


@login_required
@user_passes_test(is_instructor)
def edit_lesson(request, course_id, lesson_id):
    course = get_object_or_404(Course, pk=course_id, instructor=request.user)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        
        # Check if video deletion was requested
        delete_video = request.POST.get('delete_video')
        
        # Check if attachment deletion was requested
        delete_attachments = request.POST.getlist('delete_attachment')
        
        if form.is_valid():
            # Delete video if requested
            if delete_video:
                if lesson.video:
                    lesson.video.delete()
                    lesson.video = None
                    lesson.duration = 0
                    lesson.duration_seconds = 0
            
            # معالجة نوع الفيديو
            video_type = form.cleaned_data.get('video_type')
            if video_type == 'youtube':
                # إذا تم تغيير النوع من ملف إلى يوتيوب، نحذف ملف الفيديو
                if lesson.video:
                    lesson.video.delete()
                lesson.video = None
                lesson.video_type = 'youtube'
            else:
                # إذا تم تغيير النوع من يوتيوب إلى ملف، نحذف رابط اليوتيوب
                lesson.video_url = None
                lesson.video_type = 'file'
            
            # حفظ المدة بالثواني
            lesson.duration_seconds = form.cleaned_data.get('duration_seconds', 0)
            
            # Save lesson changes
            lesson = form.save()
            
            # Delete selected attachments
            if delete_attachments:
                for attachment_id in delete_attachments:
                    try:
                        attachment = LessonAttachment.objects.get(pk=attachment_id)
                        # Delete the actual file
                        attachment.attachment_file.delete()
                        # Delete the database record
                        attachment.delete()
                    except LessonAttachment.DoesNotExist:
                        pass
            
            # Process new attachment files
            for file in request.FILES.getlist('attachment_files'):
                # Extract filename without extension
                filename = os.path.splitext(file.name)[0]
                
                # Determine file type
                file_type = os.path.splitext(file.name)[1].lower().replace('.', '')
                
                # Create new attachment
                attachment = LessonAttachment(
                    lesson=lesson,
                    attachment_file=file,
                    filename=filename,
                    file_type=file_type
                )
                attachment.save()
            
            messages.success(request, 'تم تحديث الدرس بنجاح.')
            return redirect('edit_course', pk=course.id)
    else:
        form = LessonForm(instance=lesson)
    
    # Get attachments associated with the lesson
    attachments = LessonAttachment.objects.filter(lesson=lesson)
    
    return render(request, 'courses/edit_lesson.html', {
        'form': form,
        'course': course,
        'lesson': lesson,
        'attachments': attachments
    })

def get_youtube_video_info(request):
    """
    دالة API لجلب معلومات فيديو يوتيوب
    تستخدم في صفحات إنشاء وتعديل الدروس
    """
    video_id = request.GET.get('video_id')
    if not video_id:
        return JsonResponse({'error': 'معرف الفيديو مطلوب'}, status=400)
    
    try:
        # استخدام oEmbed API من يوتيوب (لا يتطلب مفتاح API)
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        oembed_response = requests.get(oembed_url, timeout=5)  # إضافة timeout لتجنب الانتظار الطويل
        
        # التحقق من نجاح الاستجابة
        if oembed_response.status_code != 200:
            return JsonResponse({
                'title': 'فيديو يوتيوب',
                'duration_minutes': 0,
                'duration_seconds': 0,
                'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
            })
            
        oembed_data = oembed_response.json()
        
        # الحصول على عنوان الفيديو
        title = oembed_data.get('title', 'فيديو يوتيوب')
        
        # محاولة الحصول على مدة الفيديو (هذا يتطلب YouTube Data API)
        # إذا لم يكن لديك مفتاح API، سنعيد مدة افتراضية
        duration_minutes = 0
        duration_seconds = 0
        
        # إذا كان لديك مفتاح YouTube API، يمكنك استخدام الكود التالي
        api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
        if api_key:
            try:
                api_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&part=contentDetails&key={api_key}"
                api_response = requests.get(api_url, timeout=5)
                
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    
                    if 'items' in api_data and len(api_data['items']) > 0:
                        # استخراج المدة بتنسيق ISO 8601 (مثل PT1H30M15S)
                        duration_iso = api_data['items'][0]['contentDetails']['duration']
                        
                        # تحويل تنسيق ISO 8601 إلى دقائق وثواني
                        hours = 0
                        minutes = 0
                        seconds = 0
                        
                        # استخراج الساعات
                        hour_match = re.search(r'(\d+)H', duration_iso)
                        if hour_match:
                            hours = int(hour_match.group(1))
                        
                        # استخراج الدقائق
                        minute_match = re.search(r'(\d+)M', duration_iso)
                        if minute_match:
                            minutes = int(minute_match.group(1))
                        
                        # استخراج الثواني
                        second_match = re.search(r'(\d+)S', duration_iso)
                        if second_match:
                            seconds = int(second_match.group(1))
                        
                        # تحويل الكل إلى دقائق وثواني
                        duration_minutes = hours * 60 + minutes
                        duration_seconds = seconds
            except Exception as api_error:
                # لا نريد أن نفشل الطلب بالكامل إذا فشل جلب المدة
                print(f"خطأ في جلب مدة الفيديو: {api_error}")
        
        return JsonResponse({
            'title': title,
            'duration_minutes': duration_minutes,
            'duration_seconds': duration_seconds,
            'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        })
    
    except Exception as e:
        # في حالة حدوث أ�� خطأ، نعيد معلومات افتراضية بدلاً من رمز خطأ
        return JsonResponse({
            'title': 'فيديو يوتيوب',
            'duration_minutes': 0,
            'duration_seconds': 0,
            'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
        })

@login_required
@user_passes_test(is_instructor)
def delete_attachment(request, attachment_id):
    """Vista para eliminar un adjunto mediante AJAX"""
    if request.method == 'POST':
        attachment = get_object_or_404(LessonAttachment, pk=attachment_id)
        lesson_id = request.POST.get('lesson_id')
        
        # Verificar que el usuario es el instructor del curso
        if lesson_id:
            lesson = get_object_or_404(Lesson, pk=lesson_id)
            if lesson.course.instructor != request.user:
                return JsonResponse({'success': False, 'error': 'No tienes permiso para eliminar este archivo'}, status=403)
            
            # Eliminar la relación
            lesson.attachments.remove(attachment)
            
            # Eliminar el archivo si no está asociado a otras lecciones
            if not attachment.lessons.exists():
                attachment.file.delete()
                attachment.delete()
                
            return JsonResponse({'success': True})
        
    return JsonResponse({'success': False, 'error': 'Solicitud inválida'}, status=400)

def lesson_detail(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)

    is_instructor = (course.instructor == request.user)

    # ترتيب الدروس
    lessons = course.lessons.order_by('order')
    lesson_list = list(lessons)
    current_index = lesson_list.index(lesson)

    prev_lesson = lesson_list[current_index - 1] if current_index > 0 else None
    next_lesson = lesson_list[current_index + 1] if current_index < len(lesson_list) - 1 else None

    # الحصول على المرفقات المرتبطة بالدرس
    attachments = LessonAttachment.objects.filter(lesson=lesson)

    return render(request, 'courses/lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson,
        'is_instructor': is_instructor,
        'completed_lessons': [],  # قيمة فارغة لأغراض الواجهة
        'lesson_completed': False,  # ليس مدعوم الآن
        'progress': 0,
        'completed_count': 0,
        'total_lessons': lessons.count(),
        'attachments': attachments,  # إضافة المرفقات إلى سياق القالب
    })

@login_required
@user_passes_test(is_instructor)
def delete_lesson(request, course_id, lesson_id):
    course = get_object_or_404(Course, pk=course_id, instructor=request.user)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    
    if request.method == 'POST':
        lesson.delete()
        messages.success(request, 'تم حذف الدرس بنجاح.')
    
    return redirect('edit_course', pk=course.id)

@login_required
def complete_lesson_ajax(request, course_id, lesson_id):
    if request.method == 'POST':
        course = get_object_or_404(Course, pk=course_id)
        lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
        
        # التحقق مما إذا كان المستخدم هو معلم الدورة
        is_instructor = course.instructor == request.user
        
        if is_instructor:
            # لا نسمح للمعلم بإكمال الدروس
            return JsonResponse({
                'success': False, 
                'message': 'غير مسموح للمعلم بإكمال الدروس'
            }, status=403)
        
        # التحقق من التسجيل في الدورة
        enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
        
        # إنشاء أو تحديث تقدم الدرس
        lesson_progress, created = LessonProgress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={'completed': True}
        )
        
        if not created:
            lesson_progress.completed = True
            lesson_progress.save()
        
        # حساب نسبة التقدم
        total_lessons = course.lessons.count()
        completed_count = LessonProgress.objects.filter(
            user=request.user,
            lesson__course=course,
            completed=True
        ).count()
        
        progress = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0
        
        # إضافة معلومات المدة إلى الاستجابة
        return JsonResponse({
            'success': True,
            'message': 'تم إكمال الدرس بنجاح',
            'progress': progress,
            'course_duration': course.duration_text,
            'completed_duration': f"{lesson.duration} دقيقة",
            'completed_count': completed_count,
            'total_lessons': total_lessons
        })
    
    return JsonResponse({'success': False, 'message': 'طلب غير صالح'}, status=400)

@login_required
@user_passes_test(is_instructor)
def update_lesson_duration(request, course_id, lesson_id):
    course = get_object_or_404(Course, pk=course_id, instructor=request.user)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    
    if request.method == 'POST':
        duration = request.POST.get('duration')
        if duration and duration.isdigit():
            lesson.duration = int(duration)
            lesson.save()
            messages.success(request, 'تم تحديث مدة الدرس بنجاح.')
        else:
            messages.error(request, 'يرجى إدخال مدة صحيحة.')
        
        return redirect('edit_lesson', course_id=course.id, lesson_id=lesson.id)
    
    return render(request, 'courses/update_duration.html', {
        'course': course,
        'lesson': lesson
    })

@login_required
def profile_view(request):
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    
    if profile.is_instructor:
        # إحصائيات المعلم
        courses_count = Course.objects.filter(instructor=user).count()
        students_count = Enrollment.objects.filter(course__instructor=user).values('user').distinct().count()
        
        # الدورات التي يقوم بتدريسها
        courses = Course.objects.filter(instructor=user)
        
        context = {
            'profile': profile,
            'courses_count': courses_count,
            'students_count': students_count,
            'courses': courses,
        }
    else:
        # إحصائيات الطالب
        enrolled_courses_count = Enrollment.objects.filter(user=user).count()
        completed_courses_count = Enrollment.objects.filter(user=user, completed=True).count()
        
        # الدورات المسجل فيها
        enrollments = Enrollment.objects.filter(user=user).select_related('course')
        
        context = {
            'profile': profile,
            'enrolled_courses_count': enrolled_courses_count,
            'completed_courses_count': completed_courses_count,
            'enrollments': enrollments,
        }
    
    return render(request, 'courses/profile.html', context)

@login_required
def profile_edit(request):
    user = request.user
    profile = get_object_or_404(UserProfile, user=user)
    
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'تم تحديث الملف الشخصي بنجاح.')
            return redirect('profile')
    else:
        form = ProfileEditForm(instance=profile)
    
    return render(request, 'courses/profile_edit.html', {
        'form': form,
        'profile': profile,
    })