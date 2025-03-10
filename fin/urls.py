from django.urls import path
from . import views

app_name = 'fin'
urlpatterns = [
    path('account/create/', views.account_create, name='account_create'),
    path('category/create/', views.category_create, name='category_create'),
    path('transaction/create/', views.transaction_create, name='transaction_create'),
]
