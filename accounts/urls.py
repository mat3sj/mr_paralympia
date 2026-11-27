from django.urls import path

from accounts import views

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('pending/', views.pending, name='pending'),
    path('language/', views.set_language, name='set_language'),
]
