from rest_framework import serializers
from review.models import Review
from review.serializers.review_response import ReviewResponseSerializer


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for Review model.
    Handles customer reviews for restaurants and menu items.
    """
    customer_name = serializers.SerializerMethodField()
    restaurant_name = serializers.SerializerMethodField()
    menu_item_name = serializers.SerializerMethodField()
    helpful_count = serializers.SerializerMethodField()
    user_has_voted_helpful = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    # Write-only fields for creating/updating
    order_id = serializers.PrimaryKeyRelatedField(
        source='order',
        queryset=None,  # Will be set in __init__
        write_only=True
    )
    restaurant_id = serializers.PrimaryKeyRelatedField(
        source='restaurant',
        queryset=None,  # Will be set in __init__
        write_only=True
    )
    menu_item_id = serializers.PrimaryKeyRelatedField(
        source='menu_item',
        queryset=None,  # Will be set in __init__
        write_only=True,
        required=False,
        allow_null=True
    )
    
    # Read-only nested fields
    response = ReviewResponseSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            'id',
            'customer_name',
            'order_id',
            'restaurant_id',
            'restaurant_name',
            'menu_item_id',
            'menu_item_name',
            'rating',
            'comment',
            'is_anonymous',
            'response',
            'helpful_count',
            'user_has_voted_helpful',
            'can_edit',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'customer_name',
            'helpful_count',
            'user_has_voted_helpful',
            'created_at',
            'updated_at'
        ]

    def __init__(self, *args, **kwargs):
        """
        Initialize queryset for related fields dynamically.
        """
        super().__init__(*args, **kwargs)
        
        # Import here to avoid circular imports
        from order.models import Order
        from restaurant.models import Restaurant, MenuItem
        
        self.fields['order_id'].queryset = Order.objects.all()
        self.fields['restaurant_id'].queryset = Restaurant.objects.filter(is_active=True)
        self.fields['menu_item_id'].queryset = MenuItem.objects.filter(is_active=True)

    def get_customer_name(self, obj):
        """
        Return 'Anonymous' if review is anonymous, otherwise return username.
        """
        return obj.get_display_name()

    def get_restaurant_name(self, obj):
        """
        Return restaurant name.
        """
        return obj.restaurant.name if obj.restaurant else None

    def get_menu_item_name(self, obj):
        """
        Return menu item name if exists.
        """
        return obj.menu_item.name if obj.menu_item else None

    def get_helpful_count(self, obj):
        """
        Return count of helpful votes.
        """
        return obj.get_helpful_count()

    def get_user_has_voted_helpful(self, obj):
        """
        Check if current user has voted this review as helpful.
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.helpful_votes.filter(user=request.user, is_helpful=True).exists()

    def get_can_edit(self, obj):
        """
        Check if review can be edited (within 6 hours).
        """
        return obj.can_edit()

    def validate(self, attrs):
        """
        Validate review data:
        1. User must be a customer (role=1)
        2. Order must belong to the customer
        3. Order must be in completed status (5, 6, or 7) - spam protection
        4. Menu item must be in the order (if provided)
        5. Restaurant must match order's restaurant
        6. On update, check if still within edit window for rating/comment changes
        """
        request = self.context.get('request')
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({
                'detail': 'Authentication required.'
            })

        # Check user role
        user_role = getattr(request.user, 'role', None)
        if user_role != 1:
            raise serializers.ValidationError({
                'detail': 'Only customers can create reviews.'
            })

        # Get order
        order = attrs.get('order')
        
        # Spam protection: Verify order belongs to customer
        if order.customer != request.user:
            raise serializers.ValidationError({
                'order': 'You can only review your own orders.'
            })

        # Spam protection: Verify order is in completed status
        if order.status not in [5, 6, 7]:  # Delivered, Cancelled, Completed
            raise serializers.ValidationError({
                'order': 'You can only review completed orders.'
            })

        # Verify menu item is in the order (if provided)
        menu_item = attrs.get('menu_item')
        if menu_item:
            order_menu_items = order.order_items.values_list('menu_item_id', flat=True)
            if menu_item.id not in order_menu_items:
                raise serializers.ValidationError({
                    'menu_item': 'This menu item is not part of the order.'
                })

        # Verify restaurant matches order's restaurant
        restaurant = attrs.get('restaurant')
        if restaurant != order.restaurant:
            raise serializers.ValidationError({
                'restaurant': 'Restaurant must match the order\'s restaurant.'
            })

        # On update, check edit window for rating/comment changes
        if self.instance:
            # Check if rating or comment is being changed
            if 'rating' in attrs or 'comment' in attrs:
                if not self.instance.can_edit():
                    raise serializers.ValidationError({
                        'detail': 'Rating and comment can only be edited within 6 hours of creation.'
                    })
            # is_anonymous can be changed anytime (allow revealing identity)

        return attrs
