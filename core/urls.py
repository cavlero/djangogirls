from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('/demo', views.demo, name='demo'),
    path('/about', views.about, name='about'),
    path('/search', views.search, name='search'),
    path('recipes/<int:search_id>/', views.show_recipe, name='show_recipe'),
    path('/submit_search', views.submit_search, name='submit_search'),
    path('/<path:filename>', views.get_image, name='get_image'),
]