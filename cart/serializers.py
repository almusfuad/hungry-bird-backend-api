from rest_framework import serializers
from .models import Cart, CartItem, CartAddOn
from restaurant.models import MenuItem, AddOn
from payment.models import Payment


class AddCartItemSerializer(serializers.Serializer):
    menu_item = serializers.PrimaryKeyRelatedField(
        queryset=MenuItem.objects.filter(is_available=True)
    )
    quantity = serializers.IntegerField(min_value=1)


class AddCartAddonSerializer(serializers.Serializer):
    cart_item = serializers.PrimaryKeyRelatedField(
        queryset=CartItem.objects.all()
    )
    add_on = serializers.PrimaryKeyRelatedField(
        queryset=AddOn.objects.all()
    )
    quantity = serializers.IntegerField(min_value=1)


class UpdateQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)



class CartAddOnSerializer(serializers.ModelSerializer):
    """Serializer for add-ons in cart items"""
    add_on_name = serializers.CharField(source='add_on.name', read_only=True)
    add_on_price = serializers.DecimalField(
        source='add_on.price', 
        read_only=True, 
        max_digits=6, 
        decimal_places=2
    )
    total = serializers.SerializerMethodField()

    class Meta:
        model = CartAddOn
        fields = ('id', 'add_on', 'add_on_name', 'add_on_price', 'quantity', 'total')
        read_only_fields = ('id', 'add_on_name', 'add_on_price')

    def get_total(self, obj):
        return obj.get_add_on_total()


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for items in cart with nested add-ons"""
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_price = serializers.DecimalField(
        source='menu_item.price', 
        read_only=True, 
        max_digits=8, 
        decimal_places=2
    )
    menu_item_description = serializers.CharField(
        source='menu_item.description', 
        read_only=True
    )
    cart_add_ons = CartAddOnSerializer(many=True, read_only=True)
    item_total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = (
            'id', 
            'menu_item', 
            'menu_item_name', 
            'menu_item_price', 
            'menu_item_description',
            'quantity', 
            'cart_add_ons', 
            'item_total'
        )
        read_only_fields = ('id', 'menu_item_name', 'menu_item_price', 'menu_item_description')

    def get_item_total(self, obj):
        return obj.get_item_total()

    def validate_menu_item(self, value):
        """Validate that menu item is available"""
        if not value.is_available:
            raise serializers.ValidationError(f"{value.name} is not available.")
        return value


class CartSerializer(serializers.ModelSerializer):
    """Serializer for cart with nested items and add-ons"""
    customer_name = serializers.CharField(source='customer.username', read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    restaurant_phone = serializers.CharField(
        source='restaurant.phone_number', 
        read_only=True
    )
    restaurant_address = serializers.CharField(
        source='restaurant.address', 
        read_only=True
    )
    cart_items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            'id',
            'customer',
            'customer_name',
            'restaurant',
            'restaurant_name',
            'restaurant_phone',
            'restaurant_address',
            'is_active',
            'cart_items',
            'total_price',
            'items_count',
            'created_at',
            'updated_at'
        )
        read_only_fields = (
            'id',
            'customer',
            'customer_name',
            'restaurant',
            'restaurant_name',
            'restaurant_phone',
            'restaurant_address',
            'created_at',
            'updated_at'
        )

    def get_total_price(self, obj):
        return obj.get_total_price()

    def get_items_count(self, obj):
        return obj.get_items_count()


class CheckoutSerializer(serializers.Serializer):
    """Serializer for cart checkout/confirmation"""
    delivery_address = serializers.CharField(
        max_length=500,
        required=True,
        error_messages={
            'required': 'Delivery address is required for checkout.'
        }
    )
    payment_method = serializers.ChoiceField(
        choices=Payment.METHOD_CHOICES,
        required=True,
        error_messages={
            'required': 'Payment method is required for checkout.'
        }
    )
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True
    )
    
    def validate_payment_method(self, value):
        """Validate payment method is valid for online orders"""
        ONLINE_PAYMENT_METHODS = [1, 2, 9]  # COD, Stripe, Other
        if value not in ONLINE_PAYMENT_METHODS:
            raise serializers.ValidationError(
                f"Invalid payment method. Online orders accept: "
                f"1 (Cash on Delivery), 2 (Stripe), or 9 (Other)."
            )
        return value
    
    def validate(self, data):
        """Additional cross-field validation if needed"""
        return data
