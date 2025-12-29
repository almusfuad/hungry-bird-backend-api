from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.SerializerMethodField()


    class Meta:
        model = User
        fields = ['id', 'username', 'role', 'phone_number', 'password', 'role_display', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True},
        }


    def get_role_display(self, obj):
        return obj.get_role_display()

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


