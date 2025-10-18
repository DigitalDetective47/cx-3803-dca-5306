from django.urls import path
from . import views

urlpatterns = [
    path('', views.load_selection, name='load_selection'),
    path('load/<int:simulation_id>/', views.load_view, name='load_view'),
    path('api/add-item/', views.add_item, name='add_item'),
    path('api/get-items/', views.get_items, name='get_items'),
    path('api/get-simulations/', views.get_simulations, name='get_simulations'),
    path('api/create-load/', views.create_load, name='create_load'),
    path('api/create-load-with-csv/', views.create_load_with_csv, name='create_load_with_csv'),
    path('api/import-csv/', views.import_csv, name='import_csv'),
]