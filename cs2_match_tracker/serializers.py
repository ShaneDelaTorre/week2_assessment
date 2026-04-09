from django.contrib.auth.password_validation import validate_password
from django.db.models import Sum
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Map, Match, User, UserMatchStat, Weapon, WeaponStat


class WeaponStatCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeaponStat
        fields = ("stat", "weapon", "kills")

    def validate_kills(self, value):
        if value < 0:
            raise serializers.ValidationError("Kills cannot be negative.")
        return value

    def validate(self, data):
        stat = data.get("stat")
        kills = data.get("kills", 0)
        if stat:
            # Check total weapon kills against match kills
            existing_sum = (
                stat.weapon_stats.exclude(
                    pk=getattr(self.instance, "pk", None)
                ).aggregate(total=Sum("kills"))["total"]
                or 0
            )
            if existing_sum + kills > stat.kills:
                raise serializers.ValidationError(
                    "Total weapon kills cannot exceed the total kills in the match."
                )
        return data


class WeaponStatViewSerializer(serializers.ModelSerializer):
    weapon_name = serializers.CharField(source="weapon.name", read_only=True)

    class Meta:
        model = WeaponStat
        fields = ("id", "weapon", "weapon_name", "kills")


class UserMatchStatCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMatchStat
        fields = ("match", "kills", "deaths", "assists", "mvp_rounds", "score")

    def validate(self, data):
        if (
            data["kills"] < 0
            or data["deaths"] < 0
            or data["assists"] < 0
            or data["mvp_rounds"] < 0
            or data["score"] < 0
        ):
            raise serializers.ValidationError("Stats cannot be negative.")
        return data


class UserMatchStatDetailSerializer(serializers.ModelSerializer):
    weapon_stats = WeaponStatViewSerializer(many=True, read_only=True)

    class Meta:
        model = UserMatchStat
        fields = (
            "id",
            "match",
            "kills",
            "deaths",
            "assists",
            "mvp_rounds",
            "score",
            "weapon_stats",
        )


class UserMatchStatViewSerializer(serializers.ModelSerializer):
    weapon_stats = WeaponStatViewSerializer(many=True, read_only=True)

    class Meta:
        model = UserMatchStat
        fields = (
            "id",
            "match",
            "kills",
            "deaths",
            "assists",
            "mvp_rounds",
            "score",
            "weapon_stats",
        )


class MatchSerializer(serializers.ModelSerializer):
    map_name = serializers.CharField(source="map_played.name", read_only=True)

    class Meta:
        model = Match
        fields = (
            "id",
            "map_played",
            "map_name",
            "date_played",
            "result",
            "team_score",
            "opponent_score",
        )


class MatchSerializerDetail(serializers.ModelSerializer):
    user_stats = UserMatchStatViewSerializer(many=True, read_only=True)
    map_name = serializers.CharField(source="map_played.name", read_only=True)

    class Meta:
        model = Match
        fields = (
            "id",
            "map_played",
            "map_name",
            "date_played",
            "result",
            "team_score",
            "opponent_score",
            "user_stats",
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "username", "email", "rank")


class MapSerializer(serializers.ModelSerializer):
    class Meta:
        model = Map
        fields = ("name",)


class WeaponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Weapon
        fields = ("name", "weapon_type")


class UserStatsSummarySerializer(serializers.ModelSerializer):
    total_matches = serializers.SerializerMethodField()
    win_rate = serializers.SerializerMethodField()
    kill_death_ratio = serializers.SerializerMethodField()
    win_rate_by_map = serializers.SerializerMethodField()
    favorite_weapon = serializers.SerializerMethodField()

    def get_total_matches(self, obj):
        return obj.matches.count()

    def get_win_rate(self, obj):
        matches = obj.matches.all()
        total = matches.count()
        if total == 0:
            return 0
        wins = sum(1 for m in matches if m.result == Match.RESULT_CHOICES.WIN)
        return (wins / total) * 100

    def get_kill_death_ratio(self, obj):
        stats = obj.match_stats.all()
        total_kills = sum(stat.kills for stat in stats)
        total_deaths = sum(stat.deaths for stat in stats)
        if total_deaths == 0:
            return f"{total_kills}/KDR"
        return f"{total_kills / total_deaths:.2f}/KDR"

    def get_win_rate_by_map(self, obj):
        matches = obj.matches.all()
        win_rates = {}
        for match in matches:
            map_name = match.map_played.name
            if map_name not in win_rates:
                win_rates[map_name] = {"total": 0, "wins": 0}
            win_rates[map_name]["total"] += 1
            if match.result == Match.RESULT_CHOICES.WIN:
                win_rates[map_name]["wins"] += 1
        return {
            k: (v["wins"] / v["total"]) * 100 if v["total"] > 0 else 0
            for k, v in win_rates.items()
        }

    def get_favorite_weapon(self, obj):
        weapon_kills = {}
        for stat in obj.match_stats.all():
            for ws in stat.weapon_stats.all():
                weapon_name = ws.weapon.name
                weapon_kills[weapon_name] = weapon_kills.get(weapon_name, 0) + ws.kills
        if not weapon_kills:
            return None
        return max(weapon_kills, key=weapon_kills.get)

    class Meta:
        model = User
        fields = (
            "id",
            "total_matches",
            "kill_death_ratio",
            "win_rate",
            "win_rate_by_map",
            "favorite_weapon",
        )


class UserRegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(), message="Username already exists."
            )
        ],
    )
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "rank",
            "password",
            "password_confirm",
        )
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Password confirmation does not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(
            username=validated_data["username"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            email=validated_data["email"],
            rank=validated_data["rank"],
            password=validated_data["password"],
        )
        return user
