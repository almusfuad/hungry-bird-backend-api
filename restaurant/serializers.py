from rest_framework import serializers
from .models import Restaurant, MenuItem, AddOn
from django.contrib.auth import get_user_model
from hungryBird.utils import validate_image_size


User = get_user_model()


class AddOnSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddOn
        fields = ['id', 'name', 'price']


class MenuItemSerializer(serializers.ModelSerializer):
    add_ons = AddOnSerializer(many=True, read_only=True)
    restaurant_id = serializers.PrimaryKeyRelatedField(
        source='restaurant',
        read_only = True
    )

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'category', 'description', 'price', 'image', 'is_available', 'restaurant_id', 'add_ons', 'created_at', 'updated_at']


    def validate_image(self, value):
        """
        Validate image size. Max size: 1024KB (customizable via settings)
        """
        if not value:
            return value
        
        # Validate image size (1024KB default)
        validation_result = validate_image_size(value, max_size_kb=1024)
        
        if not validation_result['success']:
            raise serializers.ValidationError(validation_result['message'])
        
        return value
    

    

class RestaurantDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'phone_number']


class RestaurantSerializer(serializers.ModelSerializer):
    menu_items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'phone_number', 'image', 'menu_items']

    def validate_image(self, value):
        """
        Validate image size. Max size: 1024KB (customizable via settings)
        """
        if not value:
            return value
        
        # Validate image size (1024KB default)
        validation_result = validate_image_size(value, max_size_kb=1024)
        
        if not validation_result['success']:
            raise serializers.ValidationError(validation_result['message'])
        
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)

        request = self.context.get('request')
        view = self.context.get('view')

        # Only include drivers for my_restaurants endpoint
        if (
            request
            and request.user.is_authenticated
            and getattr(view, 'action', None) == 'my_restaurants'
        ):
            data['drivers'] = RestaurantDriverSerializer(
                instance.drivers.all(), many=True
            ).data

        return data

