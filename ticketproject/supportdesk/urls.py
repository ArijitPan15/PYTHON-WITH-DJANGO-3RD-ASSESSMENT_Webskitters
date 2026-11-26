from django.urls import path
from . import views

urlpatterns = [
    path('', views.ticket_form, name='ticket_form'),
    path('success/', views.ticket_success, name='ticket_success'),
    path('priority/', views.check_priority, name='check_priority'),
]
