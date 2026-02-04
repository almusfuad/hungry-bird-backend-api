from rest_framework import serializers
from subscriptions.models import Feature


class FeatureSerializer(serializers.ModelSerializer):
    """
    Serializer for Feature model.
    Excludes url_patterns for security (not exposed to frontend).
    """
    class Meta:
        model = Feature
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']
