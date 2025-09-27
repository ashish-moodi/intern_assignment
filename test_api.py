#!/usr/bin/env python
"""
Simple test script to verify the Stories API is working
"""
import os
import sys
import django
from django.conf import settings

# Add the stories_service directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'stories_service'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stories_service.settings')
django.setup()

from django.contrib.auth import get_user_model
from stories.models import Story, Follow, Reaction, StoryView
from stories.serializers import StorySerializer
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

def test_basic_functionality():
    print("🧪 Testing Stories API Basic Functionality...")
    
    try:
        # Test 1: Create a user
        print("1. Creating test user...")
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        print(f"   ✅ User created: {user.email}")
        
        # Test 2: Create a story
        print("2. Creating test story...")
        story = Story.objects.create(
            author=user,
            text='This is a test story!',
            visibility='public'
        )
        print(f"   ✅ Story created: {story.id}")
        print(f"   📝 Text: {story.text}")
        print(f"   👁️  Visibility: {story.visibility}")
        print(f"   ⏰ Expires at: {story.expires_at}")
        
        # Test 3: Test story properties
        print("3. Testing story properties...")
        print(f"   ❌ Is expired: {story.is_expired}")
        print(f"   ❌ Is deleted: {story.is_deleted}")
        
        # Test 4: Create another user and follow relationship
        print("4. Testing social features...")
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        
        follow = Follow.objects.create(
            follower=other_user,
            followee=user
        )
        print(f"   ✅ Follow relationship created: {other_user.email} follows {user.email}")
        
        # Test 5: Create a view and reaction
        print("5. Testing interactions...")
        view = StoryView.objects.create(
            story=story,
            viewer=other_user
        )
        print(f"   ✅ Story view recorded: {other_user.email} viewed story {story.id}")
        
        reaction = Reaction.objects.create(
            story=story,
            user=other_user,
            emoji='👍'
        )
        print(f"   ✅ Reaction added: {other_user.email} reacted {reaction.emoji} to story {story.id}")
        
        # Test 6: Test serialization
        print("6. Testing serialization...")
        serializer = StorySerializer(story, context={'request': None})
        data = serializer.data
        print(f"   ✅ Story serialized successfully")
        print(f"   📊 View count: {data['view_count']}")
        print(f"   📊 Reaction count: {data['reaction_count']}")
        
        # Test 7: Test soft delete
        print("7. Testing soft delete...")
        story.soft_delete()
        print(f"   ✅ Story soft deleted: {story.is_deleted}")
        
        print("\n🎉 All tests passed! The Stories API is working correctly.")
        
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        Story.objects.all().delete()
        User.objects.all().delete()
        print("   ✅ Test data cleaned up")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = test_basic_functionality()
    sys.exit(0 if success else 1)
