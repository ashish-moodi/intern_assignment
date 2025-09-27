from django.contrib import admin
from .models import Story, StoryAudience, StoryView, Reaction, Follow

@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'text_preview', 'visibility', 'created_at', 'expires_at', 'is_expired']
    list_filter = ['visibility', 'created_at', 'expires_at']
    search_fields = ['author__email', 'text']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['author']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if obj.text and len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Text Preview'

@admin.register(StoryAudience)
class StoryAudienceAdmin(admin.ModelAdmin):
    list_display = ['story', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['story__id', 'user__email']
    raw_id_fields = ['story', 'user']

@admin.register(StoryView)
class StoryViewAdmin(admin.ModelAdmin):
    list_display = ['story', 'viewer', 'viewed_at']
    list_filter = ['viewed_at']
    search_fields = ['story__id', 'viewer__email']
    raw_id_fields = ['story', 'viewer']

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'story', 'user', 'emoji', 'created_at']
    list_filter = ['emoji', 'created_at']
    search_fields = ['story__id', 'user__email']
    raw_id_fields = ['story', 'user']

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'followee', 'created_at']
    list_filter = ['created_at']
    search_fields = ['follower__email', 'followee__email']
    raw_id_fields = ['follower', 'followee']
