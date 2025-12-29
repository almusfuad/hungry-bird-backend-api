from rest_framework import generics, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action, api_view, permission_classes
from django.db.models import Prefetch
from django.contrib.auth import get_user_model
from hungryBird.permissions import IsRestaurantOwner
from .models import Restaurant, MenuItem, AddOn
from .serializers import RestaurantSerializer, MenuItemSerializer, AddOnSerializer

User = get_user_model()

# Create your views here.
class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer

    @property
    def user_role(self):
        """Safely returns the user role as an integer or None"""
        role = getattr(self.request.user, 'role', None)
        try:
            return int(role) if role is not None else None
        except (ValueError, TypeError):
            return None

    def get_permissions(self):
        '''Allow any one for Read, Only restaurant owners can create/update/deleter'''
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsRestaurantOwner()]
        return [AllowAny()]
        

    def get_queryset(self):
        '''
        - restaurant_owner: sees only their own restaurants
        - driver: sees only restaurants they're assigned to
        - customer: sees all active restaurants (unauthenticated too)
        '''

        # Optimize queryset to prevent N+1
        base_queryset = Restaurant.objects.filter(is_active=True).select_related(
            'owner'
        ).prefetch_related(
            Prefetch(
                'menu_items',
                MenuItem.objects.filter(is_active=True).prefetch_related('add_ons')
            ),
            'drivers'
        ).order_by('name')


        user = self.request.user
        if not user.is_authenticated:
            return base_queryset
        
        if self.user_role == 2:  # Restaurant Owner
            return base_queryset.filter(owner=user) # Restaurant owner sees only their restaurant

        elif self.user_role == 3:  # Driver
            return base_queryset.filter(drivers=user) # Driver sees only assigned restaurants
        else:
            return base_queryset
    

    def perform_create(self,  serializer):
        serializer.save(owner=self.request.user)
    
    def perform_update(self, serializer):
        restaurant = self.get_object()
        if self.user_role != 2 or restaurant.owner != self.request.user:
            raise PermissionError('Only restaurant owners can update restaurants.')
        serializer.save()
    
    def perform_destroy(self, instance):
        if self.user_role != 2 or instance.owner != self.request.user:
            raise PermissionError('Only restaurant owners can delete restaurants.')
        instance.is_active = False
        instance.save()

    @action(detail=False, methods=['get'], permission_classes=[IsRestaurantOwner])
    def my_restaurants(self, request):
        '''Custom endpoints for restaurant owners'''
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    

    @action(detail=False, methods=['patch'], permission_classes=[IsRestaurantOwner])
    def add_driver(self, request):
        """Assign a driver to a restaurant"""

        try:
            restaurant = Restaurant.objects.get(owner=request.user)
        except Restaurant.DoesNotExist:
            return Response(
                {'error': 'Restaurant not found for this user.'},
                status=status.HTTP_404_NOT_FOUND
            )

        driver_id = request.data.get('driver_id')
        if not driver_id:
            return Response(
                {'error': 'driver_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            driver = User.objects.get(id=driver_id, role=3)
        except User.DoesNotExist:
            return Response(
                {'error': 'Driver not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if restaurant.drivers.filter(id=driver.id).exists():
            return Response(
                {'error': 'Driver already assigned to this restaurant.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        restaurant.drivers.add(driver)

        return Response(
            {
                'success': f'Driver {driver.username} assigned to restaurant {restaurant.name}.'
            },
            status=status.HTTP_200_OK
        )
    

    @action(detail=False, methods=['patch'], permission_classes=[IsRestaurantOwner])
    def remove_driver(self, request):
        '''Remove a driver friom a restaurant'''

        driver_id = request.data.get('driver_id')
        if not driver_id:
            return Response(
                {'error': 'driver_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            restaurant = Restaurant.objects.get(owner=request.user)
        except Restaurant.DoesNotExist:
            return Response(
                {'error': 'Restaurant not found for this user.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            driver = restaurant.drivers.get(id=driver_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Driver not assigned to this restaurant.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        restaurant.drivers.remove(driver)
        return Response(
            {
                'success': f'Driver {driver.username} removed from restaurant {restaurant.name}.'
            },
            status=status.HTTP_200_OK
        )


class MenuItemViewSet(viewsets.ModelViewSet):
    serializer_class = MenuItemSerializer
    

    @property
    def user_role(self):
        """Safely returns the user role as an integer or None"""
        role = getattr(self.request.user, 'role', None)
        try:
            return int(role) if role is not None else None
        except (ValueError, TypeError):
            return None

    def get_permissions(self):
        '''Allow any one for Read, Only restaurant owners can create/update/deleter'''
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        elif self.action in ['menu_categories', 'add_ons']:
            return [AllowAny()]
        else:
            return [IsRestaurantOwner()]
        

    def get_queryset(self):
        '''
        - restaurant_owner: sees only their own menu items
        - customer: sees all active menu items
        '''

        # Optimize queryset to prevent N+1
        base_queryset = MenuItem.objects.filter(
            is_active=True
        ).select_related(
            'restaurant'
        ).prefetch_related(
            Prefetch(
                'add_ons',
                AddOn.objects.filter(is_active=True)
            )
        ).order_by('restaurant', 'name')


        user = self.request.user
        if not user.is_authenticated:
            return base_queryset
        
        if self.user_role == 2:  # Restaurant Owner
            return base_queryset.filter(restaurant__owner=user) # Restaurant owner sees only their menu items
        else:
            return base_queryset
    

    def perform_create(self, serializer):
        if self.user_role != 2:
            raise PermissionError('Only restaurant owners can create menu items.')
        restaurant_id = self.request.data.get('restaurant')
        restaurant = Restaurant.objects.get(id=restaurant_id)

        if restaurant.owner != self.request.user:
            raise PermissionError('You can only add menu items to your own restaurant.')
        serializer.save(restaurant=restaurant)
    
    def perform_update(self, serializer):
        menu_item = self.get_object()
        if self.user_role != 2 or menu_item.restaurant.owner != self.request.user:
            raise PermissionError('Only restaurant owners can update menu items.')
        serializer.save()
    
    def perform_destroy(self, instance):
        if self.user_role != 2 or instance.restaurant.owner != self.request.user:
            raise PermissionError('Only restaurant owners can delete menu items.')
        instance.is_active = False
        instance.save()


    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def add_ons(self, request, pk=None):
        '''Get add-ons for a specific menu item'''
        menu_item = self.get_object()
        add_ons = menu_item.add_ons.filter(is_active=True)
        serializer = AddOnSerializer(add_ons, many=True)
        return Response(serializer.data)
    

    @action(detail=False, methods=['post'], permission_classes=[IsRestaurantOwner])
    def create_add_on(self, request):
        '''Create add-ons for menu items (restaurant owners only)'''
        menu_item_id = request.data.get('menu_item')
        try:
            menu_item = MenuItem.objects.select_related('restaurant').get(id=menu_item_id)
            if menu_item.restaurant.owner != request.user:
                return Response(
                    {'error': 'You can only manage add-ons for your own menu items.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except MenuItem.DoesNotExist:
            return Response(
                {'error': 'Menu item not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AddOnSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(menu_item=menu_item)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['patch'], permission_classes=[IsRestaurantOwner])
    def update_add_on(self, request, add_on_id=None):
        '''Update add-ons for menu items (restaurant owners only)'''
        try:
            add_on = AddOn.objects.select_related('menu_item__restaurant').get(id=add_on_id)
            if add_on.menu_item.restaurant.owner != request.user:
                return Response(
                    {'error': 'You can only update add-ons for your own menu items.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except AddOn.DoesNotExist:
            return Response(
                {'error': 'Add-on not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AddOnSerializer(add_on, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['delete'], permission_classes=[IsRestaurantOwner])
    def delete_add_on(self, request, add_on_id=None):
        '''Delete add-ons for menu items (restaurant owners only)'''
        try:
            add_on = AddOn.objects.select_related('menu_item__restaurant').get(id=add_on_id)
            if add_on.menu_item.restaurant.owner != request.user:
                return Response(
                    {'error': 'You can only delete add-ons for your own menu items.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except AddOn.DoesNotExist:
            return Response(
                {'error': 'Add-on not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        add_on.is_active = False
        add_on.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
        
        
    

    @action(detail=False, methods=['get'])
    def menu_categories(self, request):
        '''Get distinct menu categories'''
        categories = MenuItem.objects.filter(is_active=True)\
            .values_list('category', flat=True).distinct()\
            .order_by('category')
        
        return Response({
            'menu_categories': [
                { 'value': category[0], 'label': category[1]}
                for category in MenuItem.CATEGORY_CHOICES
            ]
        })
    

