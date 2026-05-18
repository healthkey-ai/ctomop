from rest_framework import serializers

from omop_core.models import EpicOrganization


class EpicOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EpicOrganization
        fields = ["id", "alias", "title"]


class StartRequestSerializer(serializers.Serializer):
    organization_alias = serializers.CharField(max_length=80)


class FinishRequestSerializer(serializers.Serializer):
    code = serializers.CharField()
    state = serializers.CharField(max_length=64)
