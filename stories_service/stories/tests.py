import json
import uuid
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Story, StoryAudience, StoryView, Reaction, Follow

User = get_user_model()

class StoryModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_story_creation(self):
        story = Story.objects.create(
            author=self.user,
            text='Test story',
            visibility='public'
        )
        
        self.assertEqual(story.author, self.user)
        self.assertEqual(story.text, 'Test story')
        self.assertEqual(story.visibility, 'public')
        self.assertIsNotNone(story.expires_at)
        self.assertIsNone(story.deleted_at)
    
    def test_story_expiration(self):
        story = Story.objects.create(
            author=self.user,
            text='Test story',
            visibility='public'
        )
        
        # Story should not be expired immediately
        self.assertFalse(story.is_expired)
        
        # Manually set expiration to past
        story.expires_at = timezone.now() - timedelta(hours=1)
        story.save()
        
        self.assertTrue(story.is_expired)
    
    def test_story_soft_delete(self):
        story = Story.objects.create(
            author=self.user,
            text='Test story',
            visibility='public'
        )
        
        self.assertFalse(story.is_deleted)
        
        story.soft_delete()
        
        self.assertTrue(story.is_deleted)
        self.assertIsNotNone(story.deleted_at)

class StoryAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    def test_create_story(self):
        url = reverse('stories:story-list')
        data = {
            'text': 'Test story',
            'visibility': 'public'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        story = Story.objects.get(id=response.data['id'])
        self.assertEqual(story.author, self.user)
        self.assertEqual(story.text, 'Test story')
    
    def test_create_story_with_media(self):
        url = reverse('stories:story-list')
        data = {
            'text': 'Test story with media',
            'media_key': 'stories/test/image.jpg',
            'visibility': 'public'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        story = Story.objects.get(id=response.data['id'])
        self.assertEqual(story.media_key, 'stories/test/image.jpg')
    
    def test_create_friends_story_with_audience(self):
        url = reverse('stories:story-list')
        data = {
            'text': 'Friends only story',
            'visibility': 'friends',
            'audience_user_ids': [str(self.other_user.id)]
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        story = Story.objects.get(id=response.data['id'])
        self.assertEqual(story.visibility, 'friends')
        self.assertTrue(StoryAudience.objects.filter(story=story, user=self.other_user).exists())
    
    def test_view_story(self):
        story = Story.objects.create(
            author=self.user,
            text='Test story',
            visibility='public'
        )
        
        url = reverse('stories:story-detail', kwargs={'pk': story.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['text'], 'Test story')
    
    def test_feed_endpoint(self):
        # Create some stories
        Story.objects.create(
            author=self.user,
            text='My story',
            visibility='public'
        )
        Story.objects.create(
            author=self.other_user,
            text='Other story',
            visibility='public'
        )
        
        url = reverse('stories:feed')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_record_story_view(self):
        story = Story.objects.create(
            author=self.other_user,
            text='Test story',
            visibility='public'
        )
        
        url = reverse('stories:story-view', kwargs={'story_id': story.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(StoryView.objects.filter(story=story, viewer=self.user).exists())
    
    def test_add_reaction(self):
        story = Story.objects.create(
            author=self.other_user,
            text='Test story',
            visibility='public'
        )
        
        url = reverse('stories:story-reaction', kwargs={'story_id': story.id})
        data = {'emoji': '👍'}
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.assertTrue(Reaction.objects.filter(story=story, user=self.user, emoji='👍').exists())
    
    def test_follow_user(self):
        url = reverse('stories:follow-user', kwargs={'user_id': self.other_user.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Follow.objects.filter(follower=self.user, followee=self.other_user).exists())
    
    def test_unfollow_user(self):
        # First follow the user
        Follow.objects.create(follower=self.user, followee=self.other_user)
        
        url = reverse('stories:unfollow-user', kwargs={'user_id': self.other_user.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Follow.objects.filter(follower=self.user, followee=self.other_user).exists())
    
    def test_user_stats(self):
        # Create some test data
        story = Story.objects.create(
            author=self.user,
            text='Test story',
            visibility='public'
        )
        
        # Add a view
        StoryView.objects.create(story=story, viewer=self.other_user)
        
        # Add a reaction
        Reaction.objects.create(story=story, user=self.other_user, emoji='👍')
        
        url = reverse('stories:user-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['stories_posted'], 1)
        self.assertEqual(response.data['total_views'], 1)
        self.assertEqual(response.data['unique_viewers'], 1)

class StoryVisibilityTest(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email='author@example.com',
            password='testpass123'
        )
        self.follower = User.objects.create_user(
            email='follower@example.com',
            password='testpass123'
        )
        self.stranger = User.objects.create_user(
            email='stranger@example.com',
            password='testpass123'
        )
        
        # Create follow relationship
        Follow.objects.create(follower=self.follower, followee=self.author)
    
    def test_public_story_visibility(self):
        story = Story.objects.create(
            author=self.author,
            text='Public story',
            visibility='public'
        )
        
        # Follower should see it
        refresh = RefreshToken.for_user(self.follower)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('stories:story-detail', kwargs={'pk': story.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Stranger should also see it
        refresh = RefreshToken.for_user(self.stranger)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_friends_story_visibility(self):
        story = Story.objects.create(
            author=self.author,
            text='Friends story',
            visibility='friends'
        )
        
        # Follower should see it
        refresh = RefreshToken.for_user(self.follower)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('stories:story-detail', kwargs={'pk': story.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Stranger should not see it
        refresh = RefreshToken.for_user(self.stranger)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_private_story_visibility(self):
        story = Story.objects.create(
            author=self.author,
            text='Private story',
            visibility='private'
        )
        
        # Even follower should not see it
        refresh = RefreshToken.for_user(self.follower)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        url = reverse('stories:story-detail', kwargs={'pk': story.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Only author should see it
        refresh = RefreshToken.for_user(self.author)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)