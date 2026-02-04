from rest_framework import serializers
from subscriptions.models import SubscriptionPlan, PlanFeature
from subscriptions.serializers.feature_serializer import FeatureSerializer


class PlanFeatureSerializer(serializers.ModelSerializer):
    """
    Serializer for PlanFeature through model.
    Shows feature details with enabled status.
    """
    feature = FeatureSerializer(read_only=True)
    
    class Meta:
        model = PlanFeature
        fields = ['feature', 'is_enabled']


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """
    Serializer for SubscriptionPlan model.
    Shows only active/enabled features.
    """
    active_features = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id',
            'name',
            'price',
            'duration_days',
            'description',
            'grace_period_days',
            'active_features'
        ]
        read_only_fields = ['id']
    
    def get_active_features(self, obj):
        """
        Get only enabled features for this plan.
        
        Returns:
            list: List of enabled feature objects
        """
        enabled_plan_features = obj.planfeature_set.filter(
            is_enabled=True
        ).select_related('feature')
        
        return FeatureSerializer(
            [pf.feature for pf in enabled_plan_features],
            many=True
        ).data
