from rest_framework import permissions
from django.db.models import Q
from .models import Follow

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the snippet.
        return obj.author == request.user

class CanViewStory(permissions.BasePermission):
    """
    Custom permission to check if user can view a story based on visibility rules.
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Author can always view their own stories
        if obj.author == user:
            return True
        
        # Public stories can be viewed by anyone
        if obj.visibility == 'public':
            return True
        
        # Private stories can only be viewed by author
        if obj.visibility == 'private':
            return False
        
        # Friends stories can be viewed by followers
        if obj.visibility == 'friends':
            return Follow.objects.filter(
                follower=user,
                followee=obj.author
            ).exists()
        
        return False
