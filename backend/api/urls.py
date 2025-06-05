from django.urls import path
from . import views

urlpatterns = [
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:customer_id>/ucs/', views.uc_list, name='uc_list'),
    path('customers/<int:customer_id>/ucs/<int:uc_id>/', views.uc_detail, name='uc_detail'),
    path('customers/<int:customer_id>/ucs/<int:uc_id>/toggle/', views.uc_toggle_status, name='uc_toggle_status'),
]