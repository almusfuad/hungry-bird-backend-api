import logging
from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import generics, status, views
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import UserSerializer


logger = logging.getLogger(__name__)

# Create your views here.
@api_view(['GET'])
def get_role_choices(request):
    '''Return available role choices for frontends'''
    return Response({
        'choices': [
            {'value': choice[0], 'label': choice[1]}
            for choice in User.ROLE_CHOICES
        ]
    })


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


    def perform_create(self, serializer):
        serializer.save()
        return Response({'message': 'User registered successfully'}, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def post(self, request):
        phone_number = request.data.get('phone_number')
        password = request.data.get('password')

        try:
            user = User.objects.get(username=phone_number)
            if not user.check_password(password):
                return Response({'error': 'Invalid phone number or password'}, status=status.HTTP_400_BAD_REQUEST)
            if not user.is_active:
                return Response({'error': 'User account is disabled'}, status=status.HTTP_400_BAD_REQUEST) 
        except User.DoesNotExist:
            logger.error(f"Failed login attempt: {phone_number}")
            return Response({'error': 'Invalid phone number or password'}, status=status.HTTP_400_BAD_REQUEST)
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
    


class LogoutView(views.APIView):
    '''Logout user by blacklisting their refresh token'''
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            refresh_token = request.query_params.get('refresh')
            if not refresh_token:
                logger.error(f"Refresh token not found.")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'User logged out successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Invalid token or token has already been blacklisted'}, status=status.HTTP_400_BAD_REQUEST)

