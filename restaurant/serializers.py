from rest_framework import serializers
from .models import Restaurant, MenuItem, AddOn


class AddOnSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddOn
        fields = ['id', 'name', 'price']


class MenuItemSerializer(serializers.ModelSerializer):
    add_ons = AddOnSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'category', 'description', 'price', 'is_available', 'add_ons']


class RestaurantSerializer(serializers.ModelSerializer):
    menu_items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'menu_items', 'phone_number']