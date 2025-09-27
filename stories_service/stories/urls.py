from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'stories', views.StoryViewSet, basename='story')

urlpatterns = [
    path('', include(router.urls)),
    path('feed/', views.feed, name='feed'),
    path('stories/<uuid:story_id>/view/', views.record_story_view, name='story-view'),
    path('stories/<uuid:story_id>/reactions/', views.add_reaction, name='story-reaction'),
    path('me/stats/', views.user_stats, name='user-stats'),
    path('follow/<uuid:user_id>/', views.follow_user, name='follow-user'),
    path('unfollow/<uuid:user_id>/', views.unfollow_user, name='unfollow-user'),
    path('upload-url/', views.generate_upload_url, name='upload-url'),
    path('health/', views.health_check, name='health-check'),
]
