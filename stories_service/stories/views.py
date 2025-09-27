import json
import logging
from datetime import datetime, timedelta
from django.db import transaction
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.conf import settings
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import CursorPagination
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Story, StoryAudience, StoryView, Reaction, Follow
from .serializers import (
    StorySerializer, StoryCreateSerializer, StoryViewSerializer,
    ReactionSerializer, FollowSerializer, UserStatsSerializer,
    MediaUploadSerializer
)
from .permissions import IsOwnerOrReadOnly, CanViewStory
from .services import MediaUploadService, CacheService, NotificationService

User = get_user_model()
logger = logging.getLogger(__name__)

class StoryPagination(CursorPagination):
    page_size = 20
    ordering = '-created_at'

@extend_schema_view(
    list=extend_schema(
        summary="List Stories",
        description="Get a paginated list of stories visible to the authenticated user. Includes public stories, stories from followed users, and user's own stories.",
        tags=["Stories"],
        parameters=[
            OpenApiParameter(
                name='cursor',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Cursor for pagination'
            ),
        ],
        examples=[
            OpenApiExample(
                'Success Response',
                value={
                    "count": 25,
                    "next": "http://api/stories/?cursor=eyJpZCI6MTIzfQ",
                    "previous": None,
                    "results": [
                        {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "author": "user@example.com",
                            "text": "Hello world!",
                            "visibility": "public",
                            "created_at": "2024-01-01T12:00:00Z",
                            "expires_at": "2024-01-02T12:00:00Z",
                            "view_count": 5,
                            "reaction_count": 2,
                            "user_reaction": "👍",
                            "is_viewed": True
                        }
                    ]
                }
            )
        ]
    ),
    create=extend_schema(
        summary="Create Story",
        description="Create a new ephemeral story with text and/or media. Stories automatically expire after 24 hours.",
        tags=["Stories"],
        examples=[
            OpenApiExample(
                'Text Story',
                value={
                    "text": "Just had an amazing day at the beach! 🏖️",
                    "visibility": "public"
                }
            ),
            OpenApiExample(
                'Media Story',
                value={
                    "text": "Check out this sunset!",
                    "media_key": "stories/user123/sunset.jpg",
                    "visibility": "friends"
                }
            ),
            OpenApiExample(
                'Friends Story with Audience',
                value={
                    "text": "Private message for close friends",
                    "visibility": "friends",
                    "audience_user_ids": ["user-id-1", "user-id-2"]
                }
            )
        ]
    ),
    retrieve=extend_schema(
        summary="Get Story",
        description="Retrieve a specific story by ID. Automatically records a view if the user hasn't viewed it before.",
        tags=["Stories"]
    ),
    update=extend_schema(
        summary="Update Story",
        description="Update an existing story. Only the story author can update their stories.",
        tags=["Stories"]
    ),
    partial_update=extend_schema(
        summary="Partially Update Story",
        description="Partially update an existing story. Only the story author can update their stories.",
        tags=["Stories"]
    ),
    destroy=extend_schema(
        summary="Delete Story",
        description="Delete a story. Only the story author can delete their stories.",
        tags=["Stories"]
    )
)
class StoryViewSet(ModelViewSet):
    serializer_class = StorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    pagination_class = StoryPagination
    
    def get_serializer_class(self):
        """Return different serializers for different actions"""
        if self.action == 'create':
            return StoryCreateSerializer
        return StorySerializer
    
    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        
        # Base queryset with prefetching for performance
        queryset = Story.objects.filter(
            deleted_at__isnull=True,
            expires_at__gt=now
        ).select_related('author').prefetch_related(
            'views', 'reactions'
        ).order_by('-created_at')
        
        # Apply visibility filters
        if self.action == 'list':
            # For feed, show public stories + stories from followed users
            followed_user_ids = self.get_followed_user_ids(user)
            
            queryset = queryset.filter(
                Q(visibility='public') |
                Q(visibility='friends', author__in=followed_user_ids) |
                Q(author=user)  # User's own stories
            )
        
        return queryset
    
    def get_followed_user_ids(self, user):
        """Get cached list of followed user IDs"""
        cache_key = f"user_following:{user.id}"
        followed_ids = cache.get(cache_key)
        
        if followed_ids is None:
            followed_ids = list(Follow.objects.filter(follower=user).values_list('followee_id', flat=True))
            cache.set(cache_key, followed_ids, 300)  # Cache for 5 minutes
        
        return followed_ids
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
        elif self.action == 'retrieve':
            permission_classes = [permissions.IsAuthenticated, CanViewStory]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        user = self.request.user
        story = serializer.save(author=user)
        
        # Handle friends-only audience
        audience_user_ids = self.request.data.get('audience_user_ids', [])
        if story.visibility == 'friends' and audience_user_ids:
            with transaction.atomic():
                audience_objects = [
                    StoryAudience(story=story, user_id=user_id)
                    for user_id in audience_user_ids
                ]
                StoryAudience.objects.bulk_create(audience_objects)
        
        # Log story creation
        logger.info('story_created', extra={
            'story_id': str(story.id),
            'author_id': str(user.id),
            'visibility': story.visibility,
            'has_media': bool(story.media_key)
        })
        
        # Send real-time notification
        NotificationService.send_story_created(story)
    
    def retrieve(self, request, *args, **kwargs):
        story = self.get_object()
        
        # Record view if not already viewed
        if not story.views.filter(viewer=request.user).exists():
            StoryView.objects.create(story=story, viewer=request.user)
            
            # Send real-time notification
            NotificationService.send_story_viewed(story, request.user)
            
            logger.info('story_viewed', extra={
                'story_id': str(story.id),
                'viewer_id': str(request.user.id)
            })
        
        serializer = self.get_serializer(story)
        return Response(serializer.data)

@extend_schema(
    summary="Get User Feed",
    description="Get a personalized feed of stories for the authenticated user. Includes public stories and stories from followed users, sorted by creation date (newest first).",
    tags=["Stories"],
    parameters=[
        OpenApiParameter(
            name='cursor',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Cursor for pagination'
        ),
    ],
    examples=[
        OpenApiExample(
            'Success Response',
            value={
                "count": 15,
                "next": "http://api/feed/?cursor=eyJpZCI6MTIzfQ",
                "previous": None,
                "results": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "author": "friend@example.com",
                        "text": "Amazing sunset today!",
                        "visibility": "public",
                        "created_at": "2024-01-01T12:00:00Z",
                        "expires_at": "2024-01-02T12:00:00Z",
                        "view_count": 8,
                        "reaction_count": 3,
                        "user_reaction": "❤️",
                        "is_viewed": False
                    }
                ]
            }
        )
    ]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def feed(request):
    """Get user's feed with pagination"""
    user = request.user
    
    # Check cache first
    cache_key = f"user_feed:{user.id}:{request.GET.get('cursor', '')}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return Response(cached_result)
    
    # Get followed user IDs
    followed_user_ids = Follow.objects.filter(follower=user).values_list('followee_id', flat=True)
    
    # Build query
    now = timezone.now()
    queryset = Story.objects.filter(
        deleted_at__isnull=True,
        expires_at__gt=now
    ).filter(
        Q(visibility='public') |
        Q(visibility='friends', author__in=followed_user_ids) |
        Q(author=user)
    ).select_related('author').prefetch_related(
        'views', 'reactions'
    ).order_by('-created_at')
    
    # Apply pagination
    paginator = StoryPagination()
    page = paginator.paginate_queryset(queryset, request)
    
    if page is not None:
        serializer = StorySerializer(page, many=True, context={'request': request})
        result = paginator.get_paginated_response(serializer.data)
        
        # Cache for 30 seconds
        cache.set(cache_key, result.data, 30)
        
        return result
    
    serializer = StorySerializer(queryset, many=True, context={'request': request})
    return Response(serializer.data)

@extend_schema(
    summary="Record Story View",
    description="Record that the authenticated user has viewed a specific story. This operation is idempotent - multiple calls will only create one view record.",
    tags=["Stories"],
    examples=[
        OpenApiExample(
            'Success Response',
            value={
                "viewed": True
            }
        ),
        OpenApiExample(
            'Error - Story Not Found',
            value={
                "error": "Story not found"
            }
        ),
        OpenApiExample(
            'Error - Permission Denied',
            value={
                "error": "Permission denied"
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def record_story_view(request, story_id):
    """Record a story view (idempotent)"""
    try:
        story = Story.objects.get(id=story_id, deleted_at__isnull=True)
    except Story.DoesNotExist:
        return Response({'error': 'Story not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user can view this story
    if not CanViewStory().has_object_permission(request, None, story):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    # Create view record (idempotent)
    view, created = StoryView.objects.get_or_create(
        story=story,
        viewer=request.user
    )
    
    if created:
        # Send real-time notification
        NotificationService.send_story_viewed(story, request.user)
        
        logger.info('story_viewed', extra={
            'story_id': str(story.id),
            'viewer_id': str(request.user.id)
        })
    
    return Response({'viewed': True})

@extend_schema(
    summary="Add Story Reaction",
    description="Add or update a reaction to a story. Users can only have one reaction per story. Valid emojis: 👍 ❤️ 😂 😮 😢 🔥",
    tags=["Stories"],
    examples=[
        OpenApiExample(
            'Add Reaction',
            value={
                "emoji": "👍"
            }
        ),
        OpenApiExample(
            'Success Response',
            value={
                "id": "reaction-uuid",
                "story": "story-uuid",
                "user": "user-uuid",
                "user_email": "user@example.com",
                "emoji": "👍",
                "created_at": "2024-01-01T12:00:00Z"
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_reaction(request, story_id):
    """Add or update a reaction to a story"""
    try:
        story = Story.objects.get(id=story_id, deleted_at__isnull=True)
    except Story.DoesNotExist:
        return Response({'error': 'Story not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user can view this story
    if not CanViewStory().has_object_permission(request, None, story):
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    emoji = request.data.get('emoji')
    if not emoji:
        return Response({'error': 'Emoji is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Create or update reaction
    reaction, created = Reaction.objects.update_or_create(
        story=story,
        user=request.user,
        defaults={'emoji': emoji}
    )
    
    # Send real-time notification
    NotificationService.send_story_reacted(story, request.user, emoji)
    
    logger.info('reaction_added', extra={
        'story_id': str(story.id),
        'user_id': str(request.user.id),
        'emoji': emoji
    })
    
    serializer = ReactionSerializer(reaction)
    return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

@extend_schema(
    summary="Get User Statistics",
    description="Get comprehensive statistics for the authenticated user including story counts, views, reactions, and recent activity.",
    tags=["Analytics"],
    examples=[
        OpenApiExample(
            'Success Response',
            value={
                "stories_posted": 25,
                "total_views": 150,
                "unique_viewers": 45,
                "reaction_breakdown": {
                    "👍": 12,
                    "❤️": 8,
                    "😂": 5,
                    "😮": 3,
                    "😢": 1,
                    "🔥": 6
                },
                "last_7_days": {
                    "stories_posted": 5,
                    "views": 30
                }
            }
        )
    ]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get user statistics"""
    user = request.user
    now = timezone.now()
    week_ago = now - timedelta(days=7)
    
    # Get user's stories
    user_stories = Story.objects.filter(author=user, deleted_at__isnull=True)
    
    # Calculate stats
    stories_posted = user_stories.count()
    
    # Get view counts
    total_views = StoryView.objects.filter(story__author=user).count()
    unique_viewers = StoryView.objects.filter(story__author=user).values('viewer').distinct().count()
    
    # Reaction breakdown
    reactions = Reaction.objects.filter(story__author=user)
    reaction_breakdown = {}
    for emoji, _ in Reaction.EMOJI_CHOICES:
        reaction_breakdown[emoji] = reactions.filter(emoji=emoji).count()
    
    # Last 7 days stats
    week_stories = user_stories.filter(created_at__gte=week_ago).count()
    week_views = StoryView.objects.filter(
        story__author=user,
        viewed_at__gte=week_ago
    ).count()
    
    stats = {
        'stories_posted': stories_posted,
        'total_views': total_views,
        'unique_viewers': unique_viewers,
        'reaction_breakdown': reaction_breakdown,
        'last_7_days': {
            'stories_posted': week_stories,
            'views': week_views
        }
    }
    
    serializer = UserStatsSerializer(stats)
    return Response(serializer.data)

@extend_schema(
    summary="Follow User",
    description="Follow another user to see their friends-only stories in your feed. Users cannot follow themselves.",
    tags=["Social"],
    examples=[
        OpenApiExample(
            'Success Response',
            value={
                "message": "Successfully followed user"
            }
        ),
        OpenApiExample(
            'Error - User Not Found',
            value={
                "error": "User not found"
            }
        ),
        OpenApiExample(
            'Error - Cannot Follow Self',
            value={
                "error": "Cannot follow yourself"
            }
        ),
        OpenApiExample(
            'Error - Already Following',
            value={
                "error": "Already following this user"
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def follow_user(request, user_id):
    """Follow a user"""
    try:
        followee = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if followee == request.user:
        return Response({'error': 'Cannot follow yourself'}, status=status.HTTP_400_BAD_REQUEST)
    
    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        followee=followee
    )
    
    if not created:
        return Response({'error': 'Already following this user'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Clear cache
    cache.delete(f"user_following:{request.user.id}")
    
    logger.info('user_followed', extra={
        'follower_id': str(request.user.id),
        'followee_id': str(followee.id)
    })
    
    return Response({'message': 'Successfully followed user'}, status=status.HTTP_201_CREATED)

@extend_schema(
    summary="Unfollow User",
    description="Stop following a user. This will remove their friends-only stories from your feed.",
    tags=["Social"],
    examples=[
        OpenApiExample(
            'Success Response',
            value={
                "message": "Successfully unfollowed user"
            }
        ),
        OpenApiExample(
            'Error - Not Following',
            value={
                "error": "Not following this user"
            }
        )
    ]
)
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def unfollow_user(request, user_id):
    """Unfollow a user"""
    try:
        follow = Follow.objects.get(follower=request.user, followee_id=user_id)
        follow.delete()
        
        # Clear cache
        cache.delete(f"user_following:{request.user.id}")
        
        logger.info('user_unfollowed', extra={
            'follower_id': str(request.user.id),
            'followee_id': str(user_id)
        })
        
        return Response({'message': 'Successfully unfollowed user'})
    except Follow.DoesNotExist:
        return Response({'error': 'Not following this user'}, status=status.HTTP_404_NOT_FOUND)

@extend_schema(
    summary="Generate Media Upload URL",
    description="Generate a presigned URL for uploading media files to S3/MinIO. Supports images and videos up to 50MB.",
    tags=["Media"],
    examples=[
        OpenApiExample(
            'Request Body',
            value={
                "content_type": "image/jpeg",
                "file_size": 1048576
            }
        ),
        OpenApiExample(
            'Success Response',
            value={
                "upload_url": "https://minio.example.com/stories-media/stories/user123/image.jpg?X-Amz-Algorithm=...",
                "media_key": "stories/user123/image.jpg",
                "expires_in": 3600
            }
        ),
        OpenApiExample(
            'Error - Invalid Content Type',
            value={
                "content_type": ["Only image and video files are allowed"]
            }
        ),
        OpenApiExample(
            'Error - File Too Large',
            value={
                "file_size": ["File size cannot exceed 52428800MB"]
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_upload_url(request):
    """Generate presigned upload URL for media"""
    serializer = MediaUploadSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        upload_url = MediaUploadService().generate_presigned_url(
            content_type=serializer.validated_data['content_type'],
            file_size=serializer.validated_data['file_size'],
            user_id=request.user.id
        )
        
        return Response({
            'upload_url': upload_url['url'],
            'media_key': upload_url['key'],
            'expires_in': upload_url['expires_in']
        })
    except Exception as e:
        logger.error('upload_url_generation_failed', extra={
            'user_id': str(request.user.id),
            'error': str(e)
        })
        return Response({'error': 'Failed to generate upload URL'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@extend_schema(
    summary="Health Check",
    description="Check the health status of the API and its dependencies (database, cache). This endpoint is public and does not require authentication.",
    tags=["System"],
    examples=[
        OpenApiExample(
            'Healthy Response',
            value={
                "status": "healthy",
                "timestamp": "2024-01-01T12:00:00Z",
                "services": {
                    "database": "ok",
                    "cache": "ok"
                }
            }
        ),
        OpenApiExample(
            'Unhealthy Response',
            value={
                "status": "unhealthy",
                "error": "Database connection failed"
            }
        )
    ]
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Health check endpoint"""
    try:
        # Check database
        User.objects.count()
        
        # Check cache
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'services': {
                'database': 'ok',
                'cache': 'ok'
            }
        })
    except Exception as e:
        logger.error('health_check_failed', extra={'error': str(e)})
        return Response({
            'status': 'unhealthy',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)