from rest_framework import serializers
from .models import Match, User, UserMatchStat, WeaponStat, Map, Weapon
from django.db.models import Sum


class WeaponStatInputSerializer(serializers.ModelSerializer):
    weapon_name = serializers.CharField(source='weapon.name', read_only=True)
    class Meta:
        model = WeaponStat
        fields = ('stat', 'weapon_name', 'kills')
        
    def validate_kills(self, value):
        if value < 0:
            raise serializers.ValidationError("Kills cannot be negative.")
        return value
    
    def validate_kill_total(self, data):
        stat = data['stat']
        kills = data['kills']
        existing_sum = stat.weapon_stats.exclude(pk=self.instance.pk).aggregate(total=Sum('kills'))['total'] or 0
        if existing_sum + kills > stat.kills:
            raise serializers.ValidationError("Total weapon kills cannot exceed the total kills in the match.")
        return data

class WeaponStatViewSerializer(serializers.ModelSerializer):
    weapon_name = serializers.CharField(source='weapon.name', read_only=True)
    class Meta:
        model = WeaponStat
        fields = ('weapon_name', 'kills')

class UserMatchStatInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMatchStat
        fields = ('match', 'kills', 'deaths', 'assists', 'mvp_rounds', 'score')
    
    def validate_stats(self, data):
        if data['kills'] < 0 or data['deaths'] < 0 or data['assists'] < 0 or data['headshots'] < 0 or data['mvp_rounds'] < 0 or data['damage_dealt'] < 0:
            raise serializers.ValidationError("Stats cannot be negative.")
        return data

class UserMatchStatViewSerializer(serializers.ModelSerializer):
    weapon_stats = WeaponStatViewSerializer(many=True, read_only=True)
    class Meta:
        model = UserMatchStat
        fields = ('match', 'kills', 'deaths', 'assists', 'mvp_rounds', 'score', 'weapon_stats')

class MatchSerializer(serializers.ModelSerializer):
    map_name = serializers.CharField(source='map_played.name', read_only=True)
    class Meta:
        model = Match
        fields = ('id', 'map_name', 'date_played', 'result', 'team_score', 'opponent_score')

class MatchSerializerDetail(serializers.ModelSerializer):
    user_stats = UserMatchStatViewSerializer(many=True, read_only=True)
    map_name = serializers.CharField(source='map_played.name', read_only=True)
    class Meta:
        model = Match
        fields = ('id', 'map_name', 'date_played', 'result', 'team_score', 'opponent_score', 'user_stats')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'username', 'email', 'rank' )

class MapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Map
        fields = ('name')

class WeaponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Weapon
        fields = ('name','weapon_type')

class UserStatsSummarySerializer(serializers.Serializer):
    total_matches = serializers.IntegerField()
    win_rate = serializers.FloatField()
    kill_death_ratio = serializers.CharField()
    win_rate_by_map = serializers.DictField(child=serializers.FloatField())
    favorite_weapon = serializers.CharField()