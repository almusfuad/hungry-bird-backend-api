from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import Cart, CartItem, CartAddOn
from .serializers import (
    CartSerializer,
    AddCartItemSerializer, 
    AddCartAddonSerializer,
    UpdateQuantitySerializer,
    CheckoutSerializer
)
from hungryBird.permissions import IsCustomer


class CartViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing shopping carts.
    
    List: Get user's carts (active and inactive)
    Create: Create a new cart (requires restaurant_id)
    Retrieve: Get specific cart details
    Update: Update cart (is_active status)
    Destroy: Delete a cart
    """
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated, IsCustomer]
    lookup_field = 'id'

    def get_queryset(self):
        """Get carts for current user"""
        return Cart.objects.filter(customer=self.request.user)

    def create(self, request, *args, **kwargs):
        """Create a new cart for a restaurant"""
        from restaurant.models import Restaurant
        
        restaurant_id = request.data.get('restaurant')
        if not restaurant_id:
            return Response(
                {'restaurant': 'This field is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        
        # Check if active cart already exists
        existing_cart = Cart.objects.filter(
            customer=request.user,
            restaurant=restaurant,
            is_active=True
        ).first()
        
        if existing_cart:
            return Response(
                {'detail': f'Active cart already exists for {restaurant.name}.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create new cart
        cart = Cart.objects.create(
            customer=request.user,
            restaurant=restaurant,
            is_active=True
        )
        
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def add_item(self, request, id=None):
        """
        Add item to cart.
        Expected payload: {"menu_item": <id>, "quantity": <int>}
        """
        cart = self.get_object()

        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            cart.add_item(
                menu_item = serializer.validated_data['menu_item'],
                quantity = serializer.validated_data['quantity']
            )
        except DjangoValidationError as e:
            return Response(
                {'detail': e.message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_addon(self, request, id=None):
        """
        Add add-on to a cart item.
        Expected payload: {"cart_item": <id>, "add_on": <id>, "quantity": <int>}
        """
        cart = self.get_object()
        
        serializer = AddCartAddonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart_item = serializer.validated_data['cart_item']
        add_on = serializer.validated_data['add_on']
        quantity = serializer.validated_data['quantity']

        if cart_item.cart != cart:
            return Response(
                {'detail': 'Invalid cart item for this cart.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        CartAddOn.objects.update_or_create(
            cart_item = cart_item,
            add_on = add_on,
            defaults = {'quantity': quantity}
        )


        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def update_item_quantity(self, request, id=None):
        """
        Update quantity of an item in cart.
        Expected payload: {"cart_item_id": <id>, "quantity": <int>}
        """
        cart = self.get_object()
        cart_item_id = request.data.get('cart_item_id')

        if not cart_item_id:
            return Response(
                {'detail': 'cart_item_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = UpdateQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart=cart)
        cart_item.quantity = serializer.validated_data['quantity']
        cart_item.save(update_fields=['quantity'])

        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def update_addon_quantity(self, request, id=None):
        """
        Update quantity of an add-on in cart.
        Expected payload: {"addon_id": <id>, "quantity": <int>}
        """
        cart = self.get_object()
        addon_id = request.data.get('addon_id')

        if not addon_id:
            return Response(
                {'detail': 'addon_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UpdateQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart_add_on = get_object_or_404(
            CartAddOn, 
            id=addon_id, 
            cart_item__cart=cart
        )
        cart_add_on.quantity = serializer.validated_data['quantity']
        cart_add_on.save(update_fields=['quantity'])


        return Response(self.get_serializer(cart).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def remove_item(self, request, id=None):
        """
        Remove an item from cart.
        Expected payload: {"cart_item_id": <id>}
        """
        cart = self.get_object()
        cart_item_id = request.data.get('cart_item_id')

        if not cart_item_id:
            return Response(
                {'detail': 'cart_item_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart=cart)
        cart_item.delete()

        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def remove_addon(self, request, id=None):
        """
        Remove an add-on from a cart item.
        Expected payload: {"addon_id": <id>}
        """
        cart = self.get_object()
        addon_id = request.data.get('addon_id')

        if not addon_id:
            return Response(
                {'detail': 'addon_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart_add_on = get_object_or_404(
            CartAddOn, 
            id=addon_id, 
            cart_item__cart=cart
        )
        cart_add_on.delete()

        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def clear(self, request, id=None):
        """Clear all items from cart"""
        cart = self.get_object()
        cart.clear()
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def confirm(self, request, id=None):
        """
        Confirm cart and create order.
        Expected payload:
        {
            "delivery_address": "123 Main St",
            "payment_method": 1,  // 1=COD, 2=Stripe, 9=Other
            "latitude": 23.75,    // Optional
            "longitude": 90.39    // Optional
        }
        """
        cart = self.get_object()

        # Validate checkout data
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            order = cart.confirm(
                delivery_address=serializer.validated_data['delivery_address'],
                payment_method=serializer.validated_data['payment_method'],
                latitude=serializer.validated_data.get('latitude'),
                longitude=serializer.validated_data.get('longitude')
            )
        except DjangoValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {
                "order_id": order.id,
                "order_source": order.order_source,
                "order_source_display": order.get_order_source_display(),
                "total_price": str(order.total_price),
                "payment_method": order.payment.method,
                "payment_status": order.payment.get_status_display(),
                "detail": "Order confirmed successfully."
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def validate_checkout(self, request, id=None):
        """
        Validate if cart is ready for checkout.
        Returns validation status and any issues.
        """
        cart = self.get_object()
        
        issues = []
        
        if not cart.is_active:
            issues.append("Cart is not active.")
        
        if not cart.cart_items.exists():
            issues.append("Cart is empty.")
        
        # Check if all items are still available
        for item in cart.cart_items.select_related('menu_item'):
            if not item.menu_item.is_available:
                issues.append(f"{item.menu_item.name} is no longer available.")
        
        is_valid = len(issues) == 0
        
        return Response({
            "is_valid": is_valid,
            "issues": issues,
            "cart_id": cart.id,
            "total_price": str(cart.get_total_price()),
            "items_count": cart.get_items_count()
        })
        

