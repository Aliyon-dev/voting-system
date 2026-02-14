from rest_framework import serializers
from .models import Position, Candidate, Votes, Voter
from account.models import CustomUser


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ['id', 'name', 'max_vote', 'priority']


class CandidateSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()
    position_name = serializers.CharField(source='position.name', read_only=True)
    
    class Meta:
        model = Candidate
        fields = ['id', 'fullname', 'photo', 'photo_url', 'bio', 'position', 'position_name']
    
    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo and hasattr(obj.photo, 'url'):
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        return None


class VoteSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source='candidate.fullname', read_only=True)
    position_name = serializers.CharField(source='position.name', read_only=True)
    
    class Meta:
        model = Votes
        fields = ['id', 'candidate', 'candidate_name', 'position', 'position_name', 'voter']
        read_only_fields = ['voter']


class VoterSerializer(serializers.ModelSerializer):
    admin_email = serializers.EmailField(source='admin.email', read_only=True)
    admin_first_name = serializers.CharField(source='admin.first_name', read_only=True)
    admin_last_name = serializers.CharField(source='admin.last_name', read_only=True)
    
    class Meta:
        model = Voter
        fields = ['id', 'phone', 'otp', 'verified', 'voted', 'otp_sent', 
                  'admin_email', 'admin_first_name', 'admin_last_name']
        read_only_fields = ['otp', 'verified', 'voted', 'otp_sent']


class OTPVerificationSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=10, required=True)


class BallotSerializer(serializers.Serializer):
    """Serializer for ballot data with positions and candidates"""
    positions = PositionSerializer(many=True, read_only=True)
    candidates = serializers.SerializerMethodField()
    
    def get_candidates(self, obj):
        positions = obj.get('positions', [])
        candidates_data = {}
        for position in positions:
            candidates = Candidate.objects.filter(position=position)
            candidates_data[position.id] = CandidateSerializer(
                candidates, many=True, context=self.context
            ).data
        return candidates_data


class VotePreviewSerializer(serializers.Serializer):
    """Serializer for vote preview data"""
    votes = serializers.DictField(
        child=serializers.ListField(child=serializers.IntegerField())
    )


class VoteSubmitSerializer(serializers.Serializer):
    """Serializer for submitting votes"""
    votes = serializers.DictField(
        child=serializers.ListField(child=serializers.IntegerField())
    )


