from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import Cart, CartItem, CartAddOn
from .serializers import (
    CartSerializer, 
    CartItemSerializer, 
    CartAddOnSerializer, 
    AddCartItemSerializer, 
    AddCartAddonSerializer,
    UpdateQuantitySerializer
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
        cart = self.get_object()

        delivery_address = request.data.get('delivery_address')
        if not delivery_address:
            return Response(
                {'detail': 'delivery_address is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order = cart.confirm(delivery_address=delivery_address)
        except DjangoValidationError as e:
            return Response(
                {'detail': str(e.message)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(
            {
                "order_id": order.id,
                "total_price": str(order.total_price),
                "detail": "Order confirmed successfully."
            },
            status=status.HTTP_201_CREATED
        )
        

