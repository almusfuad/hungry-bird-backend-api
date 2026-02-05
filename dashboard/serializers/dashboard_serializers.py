from rest_framework import serializers


class DashboardResponseSerializer(serializers.Serializer):
    """Generic serializer for dashboard responses."""
    data = serializers.JSONField()
    message = serializers.CharField(required=False)


class DateRangeSerializer(serializers.Serializer):
    """Serializer for date range filters."""
    date_start = serializers.DateField(required=False)
    date_end = serializers.DateField(required=False)
    order_source = serializers.IntegerField(required=False, min_value=1, max_value=2)


class ExportRequestSerializer(serializers.Serializer):
    """Serializer for CSV export requests."""
    format = serializers.ChoiceField(choices=['json', 'csv'], default='json')
