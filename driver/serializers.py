from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import DriverProfile, DriverAvailability, DriverSchedule
from hungryBird.utils import validate_image_size

User = get_user_model()


class DriverUserSerializer(serializers.ModelSerializer):
    """Nested serializer for driver user details"""
    role_display = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number', 'role', 'role_display', 'image']
        read_only_fields = ['id', 'role', 'role_display']
    
    def get_role_display(self, obj):
        return obj.get_role_display()


class DriverProfileSerializer(serializers.ModelSerializer):
    """Serializer for driver profile with location and user details"""
    user = DriverUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=User.objects.filter(role=3),
        write_only=True
    )
    
    class Meta:
        model = DriverProfile
        fields = [
            'id', 'user', 'user_id', 'license_number', 'vehicle_details',
            'latitude', 'longitude', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_latitude(self, value):
        """Validate latitude is within valid range"""
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90 degrees.")
        return value
    
    def validate_longitude(self, value):
        """Validate longitude is within valid range"""
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180 degrees.")
        return value


class DriverAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for driver availability status with nested driver info"""
    driver = DriverUserSerializer(read_only=True)
    driver_id = serializers.PrimaryKeyRelatedField(
        source='driver',
        queryset=User.objects.filter(role=3),
        write_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DriverAvailability
        fields = [
            'id', 'driver', 'driver_id', 'status', 'status_display',
            'manual_override', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_status(self, value):
        """Validate status is one of the allowed choices"""
        valid_statuses = [choice[0] for choice in DriverAvailability.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(map(str, valid_statuses))}"
            )
        return value


class DriverScheduleSerializer(serializers.ModelSerializer):
    """Serializer for driver schedule with validation for day, time, and overlaps"""
    driver = DriverUserSerializer(read_only=True)
    driver_id = serializers.PrimaryKeyRelatedField(
        source='driver',
        queryset=User.objects.filter(role=3),
        write_only=True
    )
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = DriverSchedule
        fields = [
            'id', 'driver', 'driver_id', 'day_of_week', 'day_display',
            'start_time', 'end_time', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_day_of_week(self, value):
        """Validate day_of_week is between 0-6"""
        if not (0 <= value <= 6):
            raise serializers.ValidationError("day_of_week must be between 0 (Monday) and 6 (Sunday).")
        return value
    
    def validate(self, attrs):
        """
        Validate:
        1. end_time > start_time
        2. No overlapping schedules for the same driver on the same day
        """
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        # Validate end_time > start_time
        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time.'
                })
        
        # Check for overlapping schedules
        driver = attrs.get('driver')
        day_of_week = attrs.get('day_of_week')
        
        if driver and day_of_week is not None and start_time and end_time:
            # Get existing schedules for this driver on this day (excluding current instance if updating)
            existing_schedules = DriverSchedule.objects.filter(
                driver=driver,
                day_of_week=day_of_week,
                is_active=True
            )
            
            # Exclude current instance if updating
            if self.instance:
                existing_schedules = existing_schedules.exclude(id=self.instance.id)
            
            # Check for time overlaps
            for schedule in existing_schedules:
                # Overlap occurs if:
                # (new_start < existing_end) AND (new_end > existing_start)
                if start_time < schedule.end_time and end_time > schedule.start_time:
                    raise serializers.ValidationError({
                        'non_field_errors': [
                            f'Schedule overlaps with existing schedule: '
                            f'{schedule.get_day_of_week_display()} '
                            f'{schedule.start_time.strftime("%H:%M")}-{schedule.end_time.strftime("%H:%M")}'
                        ]
                    })
        
        return attrs
