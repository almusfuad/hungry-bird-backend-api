from rest_framework import serializers
from order.models import Order, OrderItem, OrderAddOn
from payment.models import Payment
from django.db.models import Prefetch
from django.db.transaction import atomic
from restaurant.serializers import MenuItemSerializer, RestaurantSerializer
from restaurant.models import MenuItem, AddOn, Restaurant



class OrderItemSerializer(serializers.ModelSerializer):
    menu_item = MenuItemSerializer(read_only=True)
    menu_item_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.all(), source='menu_item', write_only=True
    )
    add_ons = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=AddOn.objects.all(),
        required=False,
        write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item', 'menu_item_id', 'quantity', 'add_ons']


    def create(self, validated_data):
        add_ons = validated_data.pop('add_ons', [])
        order_item = OrderItem.objects.create(**validated_data)
        for add_on in add_ons:
            OrderAddOn.objects.create(
                order_item=order_item,
                add_on=add_on
            )
        return order_item
    


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    payment_method = serializers.ChoiceField(
        choices=Payment.METHOD_CHOICES, write_only=True
    )
    restaurant = RestaurantSerializer(read_only=True)
    restaurant_id = serializers.PrimaryKeyRelatedField(
        queryset=Restaurant.objects.all(), source='restaurant', write_only=True
    ) 


    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'restaurant', 'restaurant_id', 
            'status', 'total_price', 'delivery_address', 
            'items', 'payment_method', 'created_at',
            'latitude', 'longitude'
        ]
        read_only_fields = ['id', 'customer', 'status', 'total_price', 'restaurant']


    def create(self, validated_data):
        items = validated_data.pop('items')
        payment_method = validated_data.pop('payment_method')
        with atomic():
            order = Order.objects.create(
                customer=self.context['request'].user,
                **validated_data
            )
            total = 0
            for item_data in items: 
                order_item = self.fields['items'].child.create(item_data)
                order_item.order = order
                order_item.save()
                total += order_item.get_item_total()
                for add_on in order_item.order_add_ons.all():
                    total += add_on.get_add_on_total()
            order.total_price = total
            order.save()
            Payment.objects.create(
                order=order,
                method=payment_method,
                amount=total,
                status=0
            )
            return order
        

        

