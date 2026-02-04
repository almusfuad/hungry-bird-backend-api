from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from subscriptions.models import SubscriptionPlan
from subscriptions.serializers import SubscriptionPlanSerializer


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing available subscription plans.
    Read-only - plans are managed through admin interface.
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True).prefetch_related(
        'planfeature_set__feature'
    )
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]
