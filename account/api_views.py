from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import login, logout
from .email_backend import EmailBackend
from .forms import CustomUserForm
from voting.forms import VoterForm
from account.models import CustomUser
from voting.models import Voter


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """API endpoint for user login"""
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = EmailBackend.authenticate(request, username=email, password=password)
    
    if user is not None:
        login(request, user)
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type,
            }
        }, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    """API endpoint for user registration"""
    user_data = {
        'email': request.data.get('email'),
        'password': request.data.get('password'),
        'first_name': request.data.get('first_name'),
        'last_name': request.data.get('last_name'),
    }
    
    voter_data = {
        'phone': request.data.get('phone'),
    }
    
    user_form = CustomUserForm(user_data)
    voter_form = VoterForm(voter_data)
    
    if user_form.is_valid() and voter_form.is_valid():
        user = user_form.save(commit=False)
        voter = voter_form.save(commit=False)
        voter.admin = user
        voter.verified = True  # Auto-verify new voters (OTP disabled)
        voter.otp = None  # No OTP needed
        user.save()
        voter.save()
        
        # Auto-login after registration
        login(request, user)
        
        return Response({
            'success': True,
            'message': 'Account created successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type,
            }
        }, status=status.HTTP_201_CREATED)
    else:
        errors = {}
        if not user_form.is_valid():
            errors.update(user_form.errors)
        if not voter_form.is_valid():
            errors.update(voter_form.errors)
        
        return Response(
            {'error': 'Validation failed', 'errors': errors},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """API endpoint for user logout"""
    logout(request)
    return Response({
        'success': True,
        'message': 'Logged out successfully'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_user_profile(request):
    """API endpoint to get current user profile"""
    user = request.user
    voter_data = None
    
    if hasattr(user, 'voter'):
        voter = user.voter
        voter_data = {
            'phone': voter.phone,
            'verified': voter.verified,
            'voted': voter.voted,
        }
    
    return Response({
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user.user_type,
            'voter': voter_data,
        }
    }, status=status.HTTP_200_OK)

