from django.urls import path
from . import views

urlpatterns = [
    path('initiate/', views.initiate_payment, name='initiate-payment'),
    path('status/<str:reference>/', views.payment_status, name='payment-status'),
    path('callback/', views.momo_callback, name='momo-callback'),
]
