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
            'id', 'customer', 'restaurant_id', 'status',
            'status', 'total_price', 'delivery_address',
            'items', 'payment_method',
            'latitude', 'longitude', 'created_at'
        ]
        read_only_fields = ['id', 'total_price', 'customer', 'created_at']

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
        

        

    def update(self, instance, validated_data):
        request = self.context['request']
        user = request.user


        # status update
        if 'status' in validated_data:
            instance.transition_status(
                user, validated_data['status']
            )

        # Item updates (customer only)
        items_data = validated_data.pop('items', None)
        if items_data is not None:
            if int(user.role) != 1:
                raise serializers.ValidationError(
                    "Only customers can update order items."
                )
            if not instance.can_edit():
                raise serializers.ValidationError(
                    "Order cannot be edited at this stage."
                )
            
            self._sync_order_items(instance, items_data)

            instance.total_price = instance.get_order_total()
            instance.save(update_fields=['total_price'])
        return instance
    

    # synchronize order items with provided data
    def _sync_order_items(self, order, items_data):
        existing_items = {
            item.id: item for item in order.order_items.all()
        }
        incoming_item_ids = set()

        for item_data in items_data:
            item_id = item_data.get('id')
            add_ons = item_data.pop('add_ons', [])

            if item_id and item_id in existing_items:
                order_item = existing_items[item_id]
                order_item.quantity = item_data.get(
                    'quantity', order_item.quantity
                )
                order_item.save()
                self._sync_add_ons(order_item, add_ons)
                incoming_item_ids.add(item_id)
            else:
                order_item = OrderItem.objects.create(
                    order=order,
                    **item_data
                )
                self._sync_add_ons(order_item, add_ons)
                incoming_item_ids.add(order_item.id)


        # Remove items not in incoming data
        for item_id, order_item in existing_items.items():
            if item_id not in incoming_item_ids:
                order_item.delete()


    
    # synchronize add-ons for an order item
    def _sync_add_ons(self, order_item, add_ons):
        existing = {
            ao.add_on_id: ao for ao in order_item.order_add_ons.all()
        }
        incoming_ao_ids = set()

        for ao in add_ons:
            ao_id = ao['id']
            qty = ao['quantity']

            if ao_id in existing:
                existing[ao_id].quantity = qty
                existing[ao_id].save()
            else:
                OrderAddOn.objects.create(
                    order_item=order_item,
                    add_on_id=ao_id,
                    quantity=qty
                )

            incoming_ao_ids.add(ao_id)

    
        # Remove add-ons not in incoming data
        for ao_id, order_add_on in existing.items():
            if ao_id not in incoming_ao_ids:
                order_add_on.delete()


