from rest_framework import serializers
from order.models import Order, OrderItem, OrderAddOn
from payment.models import Payment
from django.db.models import Prefetch
from django.db.transaction import atomic
from restaurant.serializers import MenuItemSerializer, RestaurantSerializer
from restaurant.models import MenuItem, AddOn, Restaurant

class OrderAddOnSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

    def validate_id(self, value):
        if not AddOn.objects.filter(id=value).exists():
            raise serializers.ValidationError("Add-on does not exist.")
        return value
    

class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_id = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.all(),
        source='menu_item',
        write_only=True
    )
    add_ons = OrderAddOnSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = OrderItem
        fields = ['menu_item_id', 'quantity', 'add_ons']

    def create(self, validated_data):
        add_ons_data = validated_data.pop('add_ons', [])
        order = self.context['order']

        order_item = OrderItem.objects.create(order=order, **validated_data)

        for add_on_data in add_ons_data:
            OrderAddOn.objects.create(
                order_item=order_item,
                add_on_id=add_on_data['id'],
                quantity=add_on_data['quantity']
            )

        return order_item

    


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, write_only=True)
    payment_method = serializers.ChoiceField(
        choices=Payment.METHOD_CHOICES, write_only=True
    )
    restaurant_id = serializers.PrimaryKeyRelatedField(
        queryset=Restaurant.objects.all(),
        source='restaurant',
        write_only=True
    )

    class Meta:
        model = Order
        fields = [
            'id', 'customer', 'restaurant_id',
            'status', 'total_price', 'delivery_address',
            'items', 'payment_method',
            'latitude', 'longitude', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'total_price', 'customer']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        payment_method = validated_data.pop('payment_method')
        user = self.context['request'].user

        with atomic():
            order = Order.objects.create(
                customer=user,
                total_price=0,
                **validated_data
            )

            total = 0

            for item_data in items_data:
                add_ons_data = item_data.pop('add_ons', [])
                order_item = OrderItem.objects.create(
                    order=order,
                    **item_data
                )
                for add_on_data in add_ons_data:
                    OrderAddOn.objects.create(
                        order_item=order_item,
                        add_on_id=add_on_data['id'],
                        quantity=add_on_data['quantity']
                    )
                total += order_item.get_item_total()
                total += sum(
                    add_on.get_add_on_total()
                    for add_on in order_item.order_add_ons.all()
                )

            order.total_price = total
            order.save(update_fields=['total_price'])

            Payment.objects.create(
                order=order,
                method=payment_method,
                amount=total,
                status=0
            )

        return order
    


    # Custom representation to include nested details
    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Restaurant details
        data['restaurant'] = {
            'id': instance.restaurant.id,
            'name': instance.restaurant.name,
            'address': instance.restaurant.address,
        }

        # Order items
        items_qs = (
            instance.order_items
            .all()
            .select_related('menu_item')
            .prefetch_related('order_add_ons__add_on')
        )

        data['items'] = []
        for item in items_qs:
            item_data = {
                'id': item.id,
                'menu_item': {
                    'id': item.menu_item.id,
                    'name': item.menu_item.name,
                    'price': str(item.menu_item.price),
                },
                'quantity': item.quantity,
                'add_ons': []
            }


            for add_on in item.order_add_ons.all():
                item_data['add_ons'].append({
                    'id': add_on.add_on.id,
                    'name': add_on.add_on.name,
                    'price': str(add_on.add_on.price),
                    'quantity': add_on.quantity
                })
                
            data['items'].append(item_data)
            data['driver'] = {
                'id': instance.driver.id,
                'phone_number': instance.driver.phone_number,
                'name': instance.driver.get_full_name(),
            } if instance.driver else None


        return data
        

        

