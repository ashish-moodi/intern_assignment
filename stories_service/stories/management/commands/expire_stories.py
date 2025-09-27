import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from stories.models import Story

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Expire stories that have passed their expiration time'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Interval in seconds between runs (default: 60)'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once and exit'
        )
    
    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting story expiration worker (interval: {interval}s)')
        )
        
        while True:
            try:
                self.expire_stories()
            except Exception as e:
                logger.error('story_expiration_error', extra={'error': str(e)})
                self.stdout.write(
                    self.style.ERROR(f'Error during story expiration: {e}')
                )
            
            if run_once:
                break
            
            time.sleep(interval)
    
    def expire_stories(self):
        """Find and soft-delete expired stories"""
        now = timezone.now()
        
        # Find stories that are expired but not yet deleted
        expired_stories = Story.objects.filter(
            expires_at__lt=now,
            deleted_at__isnull=True
        )
        
        count = expired_stories.count()
        
        if count == 0:
            self.stdout.write('No expired stories found')
            return
        
        # Soft delete expired stories in batches
        batch_size = 100
        total_deleted = 0
        
        with transaction.atomic():
            for story in expired_stories.iterator(chunk_size=batch_size):
                story.soft_delete()
                total_deleted += 1
        
        # Log the expiration
        logger.info('stories_expired', extra={
            'count': total_deleted,
            'timestamp': now.isoformat()
        })
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully expired {total_deleted} stories')
        )
