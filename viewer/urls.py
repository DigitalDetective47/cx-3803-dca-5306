from django.urls import path
from . import views

urlpatterns = [
    path('', views.load_selection, name='load_selection'),
    path('load/<int:simulation_id>/', views.load_view, name='load_view'),
    path('api/add-item/', views.add_item, name='add_item'),
    path('api/get-items/', views.get_items, name='get_items'),
    path('api/get-simulations/', views.get_simulations, name='get_simulations'),
    # path('api/create-load/', views.create_load, name='create_load'),
    path('api/create-load-with-csv/', views.create_load_with_csv, name='create_load_with_csv'),
    path('api/set-sim-position/', views.set_sim_position, name='set_sim_position'),
    path('api/get-simplacements/', views.get_simplacements, name='get-simplacements'),
    # path('api/import-csv/', views.import_csv, name='import_csv'),
    path('api/delete-item/<str:item_id>/', views.delete_item, name='delete-item'),
    path("api/delete-load/<int:load_id>/", views.delete_load, name="delete_load"),
    path("api/run-algo/<int:simulation_id>/", views.run_algo, name="run_algo"),
    path("api/save-config/<int:simulation_id>/", views.save_configuration, name="save_configuration"),
    path("api/list-configs/<int:simulation_id>/", views.list_configurations, name="list_configurations"),
    path("api/load-config/<int:config_id>/", views.load_configuration, name="load_configuration"),
    path("api/delete-config/<int:config_id>/", views.delete_configuration, name="delete_configuration"),

]