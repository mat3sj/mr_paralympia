from django.urls import path

from accounts import views

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('waiting-for-approval/', views.waiting_for_approval, name='waiting_for_approval'),
    path('language/', views.switch_language, name='switch_language'),
]
