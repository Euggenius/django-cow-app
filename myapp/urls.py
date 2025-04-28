from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload, name='upload'),

    # path('select-mode/', views.select_mode, name='select_mode'),
    path('optimal-pairing/', views.optimal_pairing_form, name='optimal_pairing_page'),
    path('auto-pairing/', views.auto_pairing, name='auto_pairing'),
    path('download-pairing/', views.download_pairing, name='download_pairing'),
    path('reset-priorities/', views.reset_priorities, name='reset_priorities'),

    path('sort_bulls/', views.sort_bulls, name='sort_bulls'),
    path('pick-bulls/', views.pick_bulls, name='pick_bulls'),
    path('plot-results/', views.plot_results, name='plot_results'),
]
