from rest_framework.viewsets import ModelViewSet
from order.models import Order
from order.serializers import OrderSerializer
from rest_framework import status
from rest_framework.response import Response
from hungryBird.permissions import IsCustomer, IsRestaurantOwner, IsDriver


# Create your views here.
class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer


    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve', 'partial_update']:
            permission_classes = [IsCustomer]
        elif self.action in ['partial_update', 'destroy', 'list', 'retrieve']:
            permission_classes = [IsRestaurantOwner]
        elif self.action in ['list']:
            permission_classes = [IsDriver]
        else:
            permission_classes = []
        return [permission() for permission in permission_classes]
    

    def perform_create(self, serializer):
        if int(self.request.user.role) != 1:
            return Response(
                {'error': 'Only customers can place orders.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer.save()


    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'role'):
            if int(user.role) == 1:  # Customer
                return Order.objects.filter(customer=user)
            elif int(user.role) == 2:  # Restaurant Owner
                return Order.objects.filter(restaurant__owner=user)
            elif int(user.role) == 3:  # Driver
                return Order.objects.filter(driver=user)
        return Order.objects.none()