from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from hungryBird.permissions import IsDriver
from .models import DriverProfile, DriverAvailability, DriverSchedule
from .serializers import (
    DriverProfileSerializer,
    DriverAvailabilitySerializer,
    DriverScheduleSerializer
)

User = get_user_model()


class DriverProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing driver profiles.
    Drivers can view and update their own profile, including location.
    """
    serializer_class = DriverProfileSerializer
    permission_classes = [IsAuthenticated, IsDriver]
    
    def get_queryset(self):
        """Drivers can only see their own profile"""
        return DriverProfile.objects.filter(user=self.request.user).select_related('user')
    
    @action(detail=False, methods=['get'])
    def get_profile(self, request):
        """
        Get the current driver's profile.
        
        Returns:
            200: Driver profile data
            404: Profile not found (driver needs to create profile)
        """
        try:
            profile = DriverProfile.objects.select_related('user').get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DriverProfile.DoesNotExist:
            return Response(
                {'error': 'Driver profile not found. Please create a profile first.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['patch'])
    def update_location(self, request):
        """
        Update driver's current location (latitude and longitude).
        
        Expected payload:
        {
            "latitude": 40.7128,
            "longitude": -74.0060
        }
        
        Returns:
            200: Location updated successfully
            400: Invalid data
            404: Profile not found
        """
        try:
            profile = DriverProfile.objects.get(user=request.user)
        except DriverProfile.DoesNotExist:
            return Response(
                {'error': 'Driver profile not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if latitude is None or longitude is None:
            return Response(
                {'error': 'Both latitude and longitude are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate ranges
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            
            if not (-90 <= latitude <= 90):
                return Response(
                    {'error': 'Latitude must be between -90 and 90.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not (-180 <= longitude <= 180):
                return Response(
                    {'error': 'Longitude must be between -180 and 180.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid latitude or longitude format.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        profile.latitude = latitude
        profile.longitude = longitude
        profile.save()
        
        serializer = self.get_serializer(profile)
        return Response(
            {
                'message': 'Location updated successfully.',
                'profile': serializer.data
            },
            status=status.HTTP_200_OK
        )


class DriverAvailabilityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing driver availability status.
    Drivers can view and toggle their availability.
    """
    serializer_class = DriverAvailabilitySerializer
    permission_classes = [IsAuthenticated, IsDriver]
    
    def get_queryset(self):
        """Drivers can only see their own availability"""
        return DriverAvailability.objects.filter(driver=self.request.user).select_related('driver')
    
    @action(detail=False, methods=['get'])
    def get_status(self, request):
        """
        Get the current driver's availability status.
        
        Returns:
            200: Availability status data
            404: Availability record not found
        """
        try:
            availability = DriverAvailability.objects.select_related('driver').get(driver=request.user)
            serializer = self.get_serializer(availability)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except DriverAvailability.DoesNotExist:
            return Response(
                {'error': 'Availability record not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def toggle_availability(self, request):
        """
        Toggle driver's availability status manually.
        Sets manual_override=True to prevent auto-scheduling from overriding.
        
        Expected payload:
        {
            "status": 0 or 1  (0=Unavailable, 1=Available)
        }
        
        Note: Status 2 (On Delivery) is managed by the system, not manually set.
        
        Returns:
            200: Availability toggled successfully
            400: Invalid status or trying to set status=2
            404: Availability record not found
        """
        try:
            availability = DriverAvailability.objects.get(driver=request.user)
        except DriverAvailability.DoesNotExist:
            return Response(
                {'error': 'Availability record not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        new_status = request.data.get('status')
        
        if new_status is None:
            return Response(
                {'error': 'Status field is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_status = int(new_status)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Status must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Only allow manual setting of Unavailable (0) or Available (1)
        if new_status not in [0, 1]:
            return Response(
                {
                    'error': 'Manual availability can only be set to 0 (Unavailable) or 1 (Available). '
                             'Status 2 (On Delivery) is managed by the system.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status and set manual override
        availability.status = new_status
        availability.manual_override = True
        availability.save()
        
        serializer = self.get_serializer(availability)
        return Response(
            {
                'message': f'Availability set to {availability.get_status_display()}. Manual override enabled.',
                'availability': serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def enable_auto_schedule(self, request):
        """
        Re-enable automatic scheduling by setting manual_override=False.
        Driver's availability will be managed by their schedule.
        
        Returns:
            200: Auto-scheduling enabled
            404: Availability record not found
        """
        try:
            availability = DriverAvailability.objects.get(driver=request.user)
        except DriverAvailability.DoesNotExist:
            return Response(
                {'error': 'Availability record not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        availability.manual_override = False
        availability.save()
        
        serializer = self.get_serializer(availability)
        return Response(
            {
                'message': 'Auto-scheduling enabled. Your availability will be managed by your schedule.',
                'availability': serializer.data
            },
            status=status.HTTP_200_OK
        )


class DriverScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing driver schedules.
    Drivers can create, view, update, and delete their weekly schedules.
    Supports multiple schedules per day for split shifts.
    """
    serializer_class = DriverScheduleSerializer
    permission_classes = [IsAuthenticated, IsDriver]
    
    def get_queryset(self):
        """Drivers can only see their own schedules"""
        return DriverSchedule.objects.filter(driver=self.request.user).select_related('driver').order_by('day_of_week', 'start_time')
    
    def perform_create(self, serializer):
        """Automatically set the driver to the current user"""
        serializer.save(driver=self.request.user)
    
    def perform_update(self, serializer):
        """Ensure driver cannot be changed during update"""
        serializer.save(driver=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_day(self, request):
        """
        Get all schedules for a specific day.
        
        Query params:
            day: 0-6 (0=Monday, 6=Sunday)
        
        Returns:
            200: List of schedules for the specified day
            400: Invalid day parameter
        """
        day = request.query_params.get('day')
        
        if day is None:
            return Response(
                {'error': 'Day parameter is required (0-6).'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            day = int(day)
            if not (0 <= day <= 6):
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {'error': 'Day must be an integer between 0 (Monday) and 6 (Sunday).'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        schedules = self.get_queryset().filter(day_of_week=day)
        serializer = self.get_serializer(schedules, many=True)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def active_schedules(self, request):
        """
        Get all active schedules for the current driver.
        
        Returns:
            200: List of active schedules
        """
        schedules = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(schedules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
