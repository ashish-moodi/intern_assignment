import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class VisibilityChoices(models.TextChoices):
    PUBLIC = 'public', 'Public'
    FRIENDS = 'friends', 'Friends'
    PRIVATE = 'private', 'Private'

class Story(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    text = models.TextField(blank=True, null=True)
    media_key = models.CharField(max_length=500, blank=True, null=True)  # S3 object key
    visibility = models.CharField(
        max_length=20, 
        choices=VisibilityChoices.choices, 
        default=VisibilityChoices.PUBLIC
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'stories'
        indexes = [
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['deleted_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Set expiration to 24 hours from creation
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def is_deleted(self):
        return self.deleted_at is not None
    
    def soft_delete(self):
        """Soft delete the story"""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])
    
    def __str__(self):
        return f"Story {self.id} by {self.author.email}"

class StoryAudience(models.Model):
    """For friends-only stories with specific audience"""
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='audience')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='story_audiences')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'story_audience'
        unique_together = ['story', 'user']
        indexes = [
            models.Index(fields=['story']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} can view {self.story.id}"

class StoryView(models.Model):
    """Track who viewed which story"""
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='story_views')
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'story_views'
        unique_together = ['story', 'viewer']
        indexes = [
            models.Index(fields=['story']),
            models.Index(fields=['viewer']),
        ]
    
    def __str__(self):
        return f"{self.viewer.email} viewed {self.story.id}"

class Reaction(models.Model):
    """Story reactions with emoji"""
    EMOJI_CHOICES = [
        ('👍', '👍'),
        ('❤️', '❤️'),
        ('😂', '😂'),
        ('😮', '😮'),
        ('😢', '😢'),
        ('🔥', '🔥'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='story_reactions')
    emoji = models.CharField(max_length=10, choices=EMOJI_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reactions'
        unique_together = ['story', 'user']  # One reaction per user per story
        indexes = [
            models.Index(fields=['story']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.email} reacted {self.emoji} to {self.story.id}"

class Follow(models.Model):
    """Social graph for following relationships"""
    follower = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='following'
    )
    followee = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'follows'
        unique_together = ['follower', 'followee']
        indexes = [
            models.Index(fields=['follower']),
            models.Index(fields=['followee']),
        ]
    
    def __str__(self):
        return f"{self.follower.email} follows {self.followee.email}"
    
    def clean(self):
        if self.follower == self.followee:
            raise ValueError("Users cannot follow themselves")