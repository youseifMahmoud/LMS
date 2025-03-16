from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/<int:pk>/enroll/', views.enroll_course, name='enroll_course'),
    path('courses/<int:course_id>/lessons/<int:lesson_id>/', views.lesson_detail, name='lesson_detail'),
    path('courses/<int:course_id>/lessons/<int:lesson_id>/complete/', views.complete_lesson, name='complete_lesson'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('certificate/<int:enrollment_id>/', views.certificate, name='certificate'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    
    # روابط المعلم
    path('courses/create/', views.create_course, name='create_course'),
    path('courses/<int:pk>/edit/', views.edit_course, name='edit_course'),
    path('courses/<int:course_id>/lessons/create/', views.create_lesson, name='create_lesson'),
    path('courses/<int:course_id>/lessons/<int:lesson_id>/edit/', views.edit_lesson, name='edit_lesson'),
    path('courses/<int:course_id>/lessons/<int:lesson_id>/delete/', views.delete_lesson, name='delete_lesson'),
]