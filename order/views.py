from rest_framework.viewsets import ModelViewSet
from order.models import Order
from order.serializers import OrderSerializer
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from hungryBird.permissions import IsCustomer, IsRestaurantOwner, IsDriver


# Create your views here.
class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


    def get_permissions(self):
        if self.action == 'destroy':
            permission_classes = [IsCustomer]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    

    def perform_create(self, serializer):
        user_role = int(self.request.user.role)
        
        # Allow both customers (role=1) and restaurant owners (role=2)
        if user_role not in [1, 2]:
            return Response(
                {'error': 'Only customers and restaurant owners can place orders.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer.save()


    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.none()
        
        if hasattr(user, 'role'):
            if int(user.role) == 1:  # Customer
                queryset = Order.objects.filter(customer=user)
            elif int(user.role) == 2:  # Restaurant Owner
                queryset = Order.objects.filter(restaurant__owner=user)
            elif int(user.role) == 3:  # Driver
                queryset = Order.objects.filter(driver=user)
        
        # Filter by order source if provided in query params (?source=1 or ?source=2)
        source = self.request.query_params.get('source', None)
        if source:
            try:
                source = int(source)
                if source in [1, 2]:  # Valid source values
                    queryset = queryset.filter(order_source=source)
            except (ValueError, TypeError):
                pass  # Ignore invalid source values
        
        return queryset
    

    def partial_update(self, request, *args, **kwargs):
        order = self.get_object()
        serializer = self.get_serializer(
            order, data=request.data, partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    

    @action(
        detail=True, methods=['patch'],
        permission_classes=[IsAuthenticated],
        url_path='change_status'
    )
    def change_status(self, request, pk=None):
        order = self.get_object()
        new_status = request.data.get('status')

        if new_status is None:
            raise ValidationError({'error': 'Status field is required.'})
        
        try:
            new_status = int(new_status)
        except (TypeError, ValueError):
            raise ValidationError({"status": "Invalid status value."})
        
        order.transition_status(request.user, new_status)
        
        return Response(
            {
                "id": order.id,
                "status": order.status,
                "status_display": order.get_status_display(),
                "message": "Order status updated successfully."
            },
            status=status.HTTP_200_OK
        )
    