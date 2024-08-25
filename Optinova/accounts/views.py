from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from .forms import UserSignupForm
from .models import OtpToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from django.conf import settings

User = get_user_model()

@never_cache
def password_reset_request(request):
    if request.user.is_authenticated:
        return redirect('user_home') 
    if request.method == 'POST':
        email = request.POST.get('email')
        user = User.objects.filter(email=email).first()

        if user:
            otp = OtpToken.objects.create(
                user=user,
                otp_expires_at=timezone.now() + timezone.timedelta(minutes=1)  # OTP expires in 10 minutes
            )

            # Send OTP via email
            subject = "Password Reset OTP"
            message = f"Your OTP for password reset is {otp.otp_code}. It expires in 1 minutes."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

            messages.success(request, "An OTP has been sent to your email address.")
            return redirect('accounts:password_reset_verify', username=user.username)
        else:
            messages.error(request, "No user found with this email address.")

    return render(request, 'accounts/password_reset_request.html')

@never_cache
def password_reset_verify(request, username):
    if request.user.is_authenticated:
        return redirect('user_home') 
    user = get_object_or_404(User, username=username)
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        otp_record = OtpToken.objects.filter(user=user).last()

        if otp_record and otp_record.otp_code == otp_code:
            if otp_record.otp_expires_at > timezone.now():
                messages.success(request, "OTP verified! Please reset your password.")
                return redirect('accounts:password_reset_form', username=user.username)
            else:
                messages.error(request, "OTP has expired. Please request a new one.")
                return redirect('accounts:password_reset_request')
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, 'accounts/password_reset_verify.html', {'user': user})


@never_cache
def password_reset_form(request, username):
    if request.user.is_authenticated:
        return redirect('user_home') 
    user = User.objects.get(username=username)
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if new_password == confirm_password:
            user.password = make_password(new_password)
            user.save()
            messages.success(request, "Your password has been reset successfully. You can now log in.")
            return redirect('accounts:user_login_view')
        else:
            messages.error(request, "Passwords do not match. Please try again.")

    return render(request, 'accounts/password_reset_form.html', {'user': user})


@never_cache
def registration_view(request):
    if request.user.is_authenticated:
        return redirect('user_home') 
    if request.method == 'POST':
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True  
            user.save()

            # Signal will handle OTP creation and email sending

            messages.success(request, 'Account created successfully! Please check your email to verify your account.')
            return redirect('accounts:email_verify', username=user.username)
        else:
            messages.warning(request, 'Invalid form submission')
            print(f"Form errors during registration: {form.errors}")
    else:
        form = UserSignupForm()

    context = {'form': form}
    return render(request, 'accounts/registration.html', context)

@never_cache
def email_verify(request, username):
    if request.user.is_authenticated:
        return redirect('user_home') 
    user = get_object_or_404(User, username=username)
    user_otp = OtpToken.objects.filter(user=user).last()

    if not user_otp:
        messages.error(request, "No OTP found for this user.")
        return redirect('accounts:resend_otp')

    if request.method == 'POST':
        input_otp = request.POST.get('otp_code')
        
        # Validate OTP
        if user_otp.otp_code == input_otp:
            # Check for OTP expiration
            if user_otp.otp_expires_at > timezone.now():
                user.is_active = True
                user.save()
                messages.success(request, "Account activated successfully! You can now log in.")
                return redirect("accounts:user_login_view")
            else:
                messages.warning(request, "The OTP has expired. Please request a new OTP.")
                return redirect("accounts:resend_otp")
        else:
            messages.warning(request, "Invalid OTP entered. Please enter a valid OTP.")
            return redirect("accounts:email_verify", username=user.username)

    context = {'user': user}
    return render(request, "accounts/email_verify.html", context)

@never_cache
def resend_otp(request):
    if request.user.is_authenticated:
        return redirect('user_home') 
    if request.method == 'POST':
        user_email = request.POST.get("otp_email")
        user = User.objects.filter(email=user_email).first()

        if user:
            # Get the latest OTP for the user
            user_otp = OtpToken.objects.filter(user=user).last()

            if user_otp and user_otp.otp_expires_at > timezone.now():
                messages.warning(request, "Your current OTP is still valid. Please wait until it expires to request a new one.")
            else:
                # If no OTP or expired OTP, create a new one
                otp = OtpToken.objects.create(
                    user=user,
                    otp_expires_at=timezone.now() + timezone.timedelta(minutes=1)  # Set expiration time
                )

                # Email content
                subject = "Email Verification"
                message = f"""
                    Hi {user.username}, here is your new OTP {otp.otp_code}.
                    It expires in 1 minutes. Use the URL below to verify your email:
                    http://127.0.0.1:8000/email_verify/{user.username}
                """
                sender = settings.DEFAULT_FROM_EMAIL
                receiver = [user.email]

                # Send email
                send_mail(subject, message, sender, receiver, fail_silently=False)

                messages.success(request, "A new OTP has been sent to your email address.")
            return redirect('accounts:email_verify', username=user.username)
        else:
            messages.warning(request, "This email doesn't exist in our database.")
            return redirect("accounts:resend_otp")

    return render(request, "accounts/resend_otp.html")


@never_cache
def admin_login(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_page')
        else:
            messages.error(request,"You Are not allow to login ")
            return redirect('user_home')  # Redirect to user home if not authorized for admin

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            login(request, user)
            messages.success(request, 'You have successfully logged in as admin.')
            return redirect('admin_page')
        else:
            messages.error(request, 'Invalid credentials or not an admin.')

    context = {'form': form}
    return render(request, 'admin_page/admin_login.html', context)


@never_cache
def user_login_view(request):
    if request.user.is_authenticated:
        return redirect('user_home')

    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_superuser :
                messages.error(request, "Admins cannot log in through this page. Go to the admin_login page")
                return render(request,'accounts/user_login_view.html') 
            else:
                login(request, user)
                messages.success(request, 'You have successfully logged in.')
                return redirect('user_home')
        else:
            messages.error(request, "Invalid username or password.")

    context = {'form': form}
    return render(request, 'accounts/user_login_view.html', context)

@never_cache
def first_page(request):
    return render(request, 'user_home/index.html')
