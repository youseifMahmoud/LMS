from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.contrib import messages
from django.utils import timezone
from .models import Course, Lesson, Enrollment, LessonProgress

def home(request):
    featured_courses = Course.objects.all()[:3]
    return render(request, 'courses/home.html', {
        'featured_courses': featured_courses
    })

class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 9
    
    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated and hasattr(self.request.user, 'profile'):
            context['is_teacher'] = self.request.user.profile.is_teacher
        else:
            context['is_teacher'] = False
        return context

def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    is_enrolled = False
    
    if request.user.is_authenticated:
        is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'is_enrolled': is_enrolled
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
    
    # Check if user is enrolled
    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
    
    # Get lesson progress
    lesson_completed, created = LessonProgress.objects.get_or_create(
        user=request.user,
        lesson=lesson,
        defaults={'completed': False}
    )
    
    # Get completed lessons
    completed_lessons = LessonProgress.objects.filter(
        user=request.user,
        lesson__course=course,
        completed=True
    ).values_list('lesson_id', flat=True)
    
    # Calculate progress
    total_lessons = course.lessons.count()
    completed_count = len(completed_lessons)
    progress = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0
    
    # Get previous and next lessons
    lessons = list(course.lessons.order_by('order'))
    current_index = lessons.index(lesson)
    prev_lesson = lessons[current_index - 1] if current_index > 0 else None
    next_lesson = lessons[current_index + 1] if current_index < len(lessons) - 1 else None
    
    return render(request, 'courses/lesson_detail.html', {
        'course': course,
        'lesson': lesson,
        'lesson_completed': lesson_completed.completed,
        'completed_lessons': completed_lessons,
        'progress': progress,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson
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
def dashboard(request):
    active_tab = request.GET.get('tab', 'in_progress')
    
    # Get enrollments
    in_progress_enrollments = Enrollment.objects.filter(
        user=request.user,
        completed=False
    ).select_related('course')
    
    completed_enrollments = Enrollment.objects.filter(
        user=request.user,
        completed=True
    ).select_related('course')
    
    # Calculate progress for each enrollment
    for enrollment in in_progress_enrollments:
        total_lessons = enrollment.course.lessons.count()
        if total_lessons > 0:
            completed_lessons = LessonProgress.objects.filter(
                user=request.user,
                lesson__course=enrollment.course,
                completed=True
            ).count()
            enrollment.progress = int((completed_lessons / total_lessons) * 100)
        else:
            enrollment.progress = 0
    
    return render(request, 'courses/dashboard.html', {
        'in_progress_enrollments': in_progress_enrollments,
        'completed_enrollments': completed_enrollments,
        'in_progress_count': in_progress_enrollments.count(),
        'completed_count': completed_enrollments.count(),
        'active_tab': active_tab
    })

@login_required
def certificate(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id, user=request.user, completed=True)
    
    return render(request, 'courses/certificate.html', {
        'enrollment': enrollment
    })
