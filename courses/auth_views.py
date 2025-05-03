from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from .forms import UserRegistrationForm

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'تم إنشاء حساب {username} بنجاح. يمكنك الآن تسجيل الدخول.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})