from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/add-item/', views.add_item, name='add_item'),
    path('api/get-items/', views.get_items, name='get_items'),
]