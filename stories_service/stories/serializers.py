from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Story, StoryAudience, StoryView, Reaction, Follow, VisibilityChoices

User = get_user_model()

class StorySerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(
        source='author.email', 
        read_only=True,
        help_text="Email address of the story author"
    )
    author_first_name = serializers.CharField(
        source='author.first_name', 
        read_only=True,
        help_text="First name of the story author"
    )
    author_last_name = serializers.CharField(
        source='author.last_name', 
        read_only=True,
        help_text="Last name of the story author"
    )
    view_count = serializers.SerializerMethodField(
        help_text="Total number of views for this story"
    )
    reaction_count = serializers.SerializerMethodField(
        help_text="Total number of reactions for this story"
    )
    user_reaction = serializers.SerializerMethodField(
        help_text="Current user's reaction to this story (if any)"
    )
    is_viewed = serializers.SerializerMethodField(
        help_text="Whether the current user has viewed this story"
    )
    
    class Meta:
        model = Story
        fields = [
            'id', 'author', 'author_email', 'author_first_name', 'author_last_name',
            'text', 'media_key', 'visibility', 'created_at', 'expires_at',
            'view_count', 'reaction_count', 'user_reaction', 'is_viewed'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'expires_at']
        extra_kwargs = {
            'text': {
                'help_text': 'Text content of the story (optional if media is provided)',
                'required': False,
                'allow_blank': True
            },
            'media_key': {
                'help_text': 'S3 object key for media file (optional if text is provided)',
                'required': False,
                'allow_blank': True
            },
            'visibility': {
                'help_text': 'Visibility level: public, friends, or private',
                'choices': [('public', 'Public'), ('friends', 'Friends'), ('private', 'Private')]
            },
            'author': {
                'help_text': 'ID of the user who created this story'
            }
        }
    
    def get_view_count(self, obj):
        """Get the total number of views for this story"""
        return obj.views.count()
    
    def get_reaction_count(self, obj):
        """Get the total number of reactions for this story"""
        return obj.reactions.count()
    
    def get_user_reaction(self, obj):
        """Get the current user's reaction to this story"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                reaction = obj.reactions.get(user=request.user)
                return reaction.emoji
            except Reaction.DoesNotExist:
                return None
        return None
    
    def get_is_viewed(self, obj):
        """Check if the current user has viewed this story"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.views.filter(viewer=request.user).exists()
        return False

class StoryCreateSerializer(serializers.ModelSerializer):
    audience_user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        help_text="List of user IDs for friends-only stories (only used when visibility is 'friends')"
    )
    
    class Meta:
        model = Story
        fields = ['text', 'media_key', 'visibility', 'audience_user_ids']
        extra_kwargs = {
            'text': {
                'help_text': 'Text content of the story (optional if media is provided)',
                'required': False,
                'allow_blank': True
            },
            'media_key': {
                'help_text': 'S3 object key for media file (optional if text is provided)',
                'required': False,
                'allow_blank': True
            },
            'visibility': {
                'help_text': 'Visibility level: public, friends, or private',
                'choices': [('public', 'Public'), ('friends', 'Friends'), ('private', 'Private')]
            }
        }
    
    def validate_visibility(self, value):
        if value not in [choice[0] for choice in VisibilityChoices.choices]:
            raise serializers.ValidationError("Invalid visibility choice")
        return value
    
    def validate(self, attrs):
        text = attrs.get('text')
        media_key = attrs.get('media_key')
        
        if not text and not media_key:
            raise serializers.ValidationError("Either text or media_key must be provided")
        
        return attrs

class StoryViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryView
        fields = ['story', 'viewer', 'viewed_at']
        read_only_fields = ['viewer', 'viewed_at']

class ReactionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(
        source='user.email', 
        read_only=True,
        help_text="Email address of the user who reacted"
    )
    
    class Meta:
        model = Reaction
        fields = ['id', 'story', 'user', 'user_email', 'emoji', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
        extra_kwargs = {
            'story': {
                'help_text': 'ID of the story being reacted to'
            },
            'emoji': {
                'help_text': 'Emoji reaction (👍, ❤️, 😂, 😮, 😢, 🔥)',
                'choices': [('👍', '👍'), ('❤️', '❤️'), ('😂', '😂'), ('😮', '😮'), ('😢', '😢'), ('🔥', '🔥')]
            }
        }
    
    def validate_emoji(self, value):
        valid_emojis = [choice[0] for choice in Reaction.EMOJI_CHOICES]
        if value not in valid_emojis:
            raise serializers.ValidationError(f"Invalid emoji. Choose from: {', '.join(valid_emojis)}")
        return value

class FollowSerializer(serializers.ModelSerializer):
    follower_email = serializers.EmailField(
        source='follower.email', 
        read_only=True,
        help_text="Email address of the follower"
    )
    followee_email = serializers.EmailField(
        source='followee.email', 
        read_only=True,
        help_text="Email address of the user being followed"
    )
    
    class Meta:
        model = Follow
        fields = ['follower', 'follower_email', 'followee', 'followee_email', 'created_at']
        read_only_fields = ['follower', 'created_at']
        extra_kwargs = {
            'followee': {
                'help_text': 'ID of the user to follow'
            }
        }
    
    def validate(self, attrs):
        follower = self.context['request'].user
        followee = attrs['followee']
        
        if follower == followee:
            raise serializers.ValidationError("Users cannot follow themselves")
        
        if Follow.objects.filter(follower=follower, followee=followee).exists():
            raise serializers.ValidationError("Already following this user")
        
        return attrs

class UserStatsSerializer(serializers.Serializer):
    stories_posted = serializers.IntegerField(
        help_text="Total number of stories posted by the user"
    )
    total_views = serializers.IntegerField(
        help_text="Total number of views across all user's stories"
    )
    unique_viewers = serializers.IntegerField(
        help_text="Number of unique users who viewed the user's stories"
    )
    reaction_breakdown = serializers.DictField(
        help_text="Breakdown of reactions by emoji type"
    )
    last_7_days = serializers.DictField(
        help_text="Statistics for the last 7 days"
    )

class MediaUploadSerializer(serializers.Serializer):
    content_type = serializers.CharField(
        max_length=100,
        help_text="MIME type of the file (e.g., image/jpeg, video/mp4)"
    )
    file_size = serializers.IntegerField(
        min_value=1,
        help_text="Size of the file in bytes (max 50MB)"
    )
    
    def validate_content_type(self, value):
        allowed_types = ['image/', 'video/']
        if not any(value.startswith(prefix) for prefix in allowed_types):
            raise serializers.ValidationError("Only image and video files are allowed")
        return value
    
    def validate_file_size(self, value):
        max_size = 50 * 1024 * 1024  # 50MB
        if value > max_size:
            raise serializers.ValidationError(f"File size cannot exceed {max_size // (1024*1024)}MB")
        return value
