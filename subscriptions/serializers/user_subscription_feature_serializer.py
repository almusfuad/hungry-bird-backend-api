from rest_framework import serializers
from subscriptions.models import UserSubscriptionFeature, Feature
from subscriptions.serializers.feature_serializer import FeatureSerializer


class UserSubscriptionFeatureSerializer(serializers.ModelSerializer):
    """
    Serializer for per-user feature overrides.
    Used for Custom plan feature toggling.
    """
    feature = FeatureSerializer(read_only=True)
    feature_id = serializers.PrimaryKeyRelatedField(
        queryset=Feature.objects.filter(is_active=True),
        source='feature',
        write_only=True
    )
    
    class Meta:
        model = UserSubscriptionFeature
        fields = ['id', 'feature', 'feature_id', 'is_enabled']
        read_only_fields = ['id']
