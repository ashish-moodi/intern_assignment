import boto3
import uuid
import logging
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from .models import Follow

logger = logging.getLogger(__name__)

class MediaUploadService:
    """Service for handling media uploads to S3/MinIO"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=getattr(settings, 'AWS_S3_ENDPOINT_URL', None),
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    
    def generate_presigned_url(self, content_type, file_size, user_id):
        """Generate presigned URL for media upload"""
        # Generate unique key for the file
        file_extension = content_type.split('/')[-1]
        file_key = f"stories/{user_id}/{uuid.uuid4()}.{file_extension}"
        
        # Generate presigned URL
        presigned_url = self.s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': file_key,
                'ContentType': content_type,
                'ContentLength': file_size
            },
            ExpiresIn=3600  # 1 hour
        )
        
        return {
            'url': presigned_url,
            'key': file_key,
            'expires_in': 3600
        }
    
    def delete_media(self, media_key):
        """Delete media from storage"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=media_key
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete media {media_key}: {e}")
            return False

class CacheService:
    """Service for caching frequently accessed data"""
    
    @staticmethod
    def get_user_following(user_id):
        """Get cached list of users that the given user follows"""
        cache_key = f"user_following:{user_id}"
        following = cache.get(cache_key)
        
        if following is None:
            following = list(Follow.objects.filter(follower_id=user_id).values_list('followee_id', flat=True))
            cache.set(cache_key, following, 300)  # Cache for 5 minutes
        
        return following
    
    @staticmethod
    def invalidate_user_following(user_id):
        """Invalidate user following cache"""
        cache.delete(f"user_following:{user_id}")
    
    @staticmethod
    def get_feed_cache_key(user_id, cursor=None):
        """Get cache key for user feed"""
        return f"user_feed:{user_id}:{cursor or ''}"
    
    @staticmethod
    def cache_feed(user_id, feed_data, cursor=None, ttl=30):
        """Cache user feed data"""
        cache_key = CacheService.get_feed_cache_key(user_id, cursor)
        cache.set(cache_key, feed_data, ttl)

class NotificationService:
    """Service for sending real-time notifications"""
    
    @staticmethod
    def send_story_created(story):
        """Send notification when a story is created"""
        # This would integrate with WebSocket/SSE
        # For now, just log the event
        logger.info('story_created_notification', extra={
            'story_id': str(story.id),
            'author_id': str(story.author.id),
            'visibility': story.visibility
        })
    
    @staticmethod
    def send_story_viewed(story, viewer):
        """Send notification when a story is viewed"""
        # Notify the story author
        logger.info('story_viewed_notification', extra={
            'story_id': str(story.id),
            'author_id': str(story.author.id),
            'viewer_id': str(viewer.id)
        })
    
    @staticmethod
    def send_story_reacted(story, user, emoji):
        """Send notification when a story is reacted to"""
        # Notify the story author
        logger.info('story_reacted_notification', extra={
            'story_id': str(story.id),
            'author_id': str(story.author.id),
            'user_id': str(user.id),
            'emoji': emoji
        })

class RateLimitService:
    """Service for rate limiting"""
    
    @staticmethod
    def check_rate_limit(user_id, action, limit, window_seconds):
        """Check if user has exceeded rate limit for an action"""
        cache_key = f"rate_limit:{action}:{user_id}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit:
            return False
        
        # Increment counter
        cache.set(cache_key, current_count + 1, window_seconds)
        return True
    
    @staticmethod
    def get_rate_limit_info(user_id, action):
        """Get current rate limit info for user"""
        cache_key = f"rate_limit:{action}:{user_id}"
        current_count = cache.get(cache_key, 0)
        
        return {
            'current_count': current_count,
            'cache_key': cache_key
        }
