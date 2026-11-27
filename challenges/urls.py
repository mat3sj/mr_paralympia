from django.urls import path

from challenges import views

urlpatterns = [
    path('', views.home, name='home'),
    path('day/', views.day, name='day'),
    path('day/<str:date_text>/', views.day, name='day'),
    path('board/', views.board, name='board'),
    path('join/', views.join, name='join'),
    path('participants/', views.manage_participants, name='manage_participants'),
]
