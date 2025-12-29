from rest_framework import serializers
from .models import Restaurant, MenuItem, AddOn
from django.contrib.auth import get_user_model


User = get_user_model()


class AddOnSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddOn
        fields = ['id', 'name', 'price']


class MenuItemSerializer(serializers.ModelSerializer):
    add_ons = AddOnSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'category', 'description', 'price', 'is_available', 'add_ons']


class RestaurantDriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'phone_number']


class RestaurantSerializer(serializers.ModelSerializer):
    menu_items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'menu_items', 'phone_number']



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

