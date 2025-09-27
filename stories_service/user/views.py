from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import login, logout
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer
from .models import User

@extend_schema(
    summary="User Registration",
    description="Register a new user account with email and password",
    request=UserRegistrationSerializer,
    responses={
        201: UserRegistrationSerializer,
        400: OpenApiTypes.OBJECT
    },
    examples=[
        OpenApiExample(
            'Registration Example',
            value={
                "email": "user@example.com",
                "password": "securepassword123",
                "password_confirm": "securepassword123",
                "first_name": "John",
                "last_name": "Doe"
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """User registration endpoint"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': 'User created successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'created_at': user.created_at
            }
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    summary="User Login",
    description="Login with email and password to get JWT tokens",
    request=UserLoginSerializer,
    responses={
        200: OpenApiTypes.OBJECT,
        400: OpenApiTypes.OBJECT
    },
    examples=[
        OpenApiExample(
            'Login Example',
            value={
                "email": "user@example.com",
                "password": "securepassword123"
            }
        )
    ]
)
@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    """User login endpoint"""
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user)
        return Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'created_at': user.created_at
            }
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    summary="User Logout",
    description="Logout the current user",
    responses={
        200: OpenApiTypes.OBJECT
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    """User logout endpoint"""
    logout(request)
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

@extend_schema(
    summary="Get User Profile",
    description="Get the current user's profile information",
    responses={
        200: UserProfileSerializer
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get user profile"""
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)

@extend_schema(
    summary="Update User Profile",
    description="Update the current user's profile information",
    request=UserProfileSerializer,
    responses={
        200: UserProfileSerializer,
        400: OpenApiTypes.OBJECT
    },
    examples=[
        OpenApiExample(
            'Update Profile Example',
            value={
                "first_name": "John",
                "last_name": "Smith"
            }
        )
    ]
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Update user profile"""
    serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Profile updated successfully',
            'user': serializer.data
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
