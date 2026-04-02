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

class UserStatsSummarySerializer(serializers.ModelSerializer):
    total_matches = serializers.SerializerMethodField()
    win_rate = serializers.SerializerMethodField()
    kill_death_ratio = serializers.SerializerMethodField()
    win_rate_by_map = serializers.SerializerMethodField()
    favorite_weapon = serializers.SerializerMethodField()

    def get_total_matches(self, obj):
        return obj.matches.count()
    
    def get_win_rate(self, obj):
        total = obj.matches.count()
        if total == 0:
            return 0
        wins = obj.matches.filter(result=Match.RESULT_CHOICES.WIN).count()
        return (wins / total) * 100
    
    def get_kill_death_ratio(self, obj):
        stats = UserMatchStat.objects.filter(user=obj)
        total_kills = sum(stat.kills for stat in stats)
        total_deaths = sum(stat.deaths for stat in stats)
        if total_deaths == 0:
            return f"{total_kills}/KDR"
        return f"{total_kills / total_deaths:.2f}/KDR"
    
    def get_win_rate_by_map(self, obj):
        maps = Map.objects.all()
        win_rates = {}
        for match_map in maps:
            matches_on_map = obj.matches.filter(map_played=match_map)
            total = matches_on_map.count()
            if total == 0:
                win_rates[match_map.name] = 0
            else:
                wins = matches_on_map.filter(result=Match.RESULT_CHOICES.WIN).count()
                win_rates[match_map.name] = (wins / total) * 100
        return win_rates
    
    def get_favorite_weapon(self, obj):
        weapon_stats = WeaponStat.objects.filter(stat__user=obj)
        if not weapon_stats.exists():
            return None
        favorite = weapon_stats.order_by('-kills').first()
        return favorite.weapon.name
    class Meta:
        model = User
        fields = ('id', 'total_matches', 'win_rate', 'kill_death_ratio', 'win_rate_by_map', 'favorite_weapon')