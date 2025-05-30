from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'FetchVideoApp'

urlpatterns = [
    path('', views.index, name='index'),
    
    path('video/<str:video_id>/', views.video_detail, name='video_detail'),
    path('video/<str:video_id>/download/<str:video_quality>/', views.download_video_with_best_audio, name='download_video_with_best_audio'),
    path('media/<path:temp_dir>/<str:video_name>/', views.download, name='download'),

    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('privacy-policy/', views.privacypolicy, name='privacypolicy'),
    path('dmca/', views.dmca, name='dmca'),

    path('<path:undefined_path>/', views.undefined_page, name='undefined_page'),
    
] 




