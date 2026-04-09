from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, APITestCase

from .models import Map, Match, UserMatchStat, Weapon, WeaponStat
from .permissions import IsAuthenticatedAndOwner, IsAuthenticatedOrReadOnly
from .serializers import (
    MapSerializer,
    MatchSerializer,
    MatchSerializerDetail,
    UserMatchStatCreateSerializer,
    UserSerializer,
    WeaponSerializer,
    WeaponStatCreateSerializer,
    WeaponStatViewSerializer,
)

User = get_user_model()


class BaseTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="StrongPass123!", email="test@test.com"
        )

        self.other_user = User.objects.create_user(
            username="otheruser", password="StrongPass123!"
        )

        self.staff_user = User.objects.create_user(
            username="staffuser", password="StrongPass123!", is_staff=True
        )

        self.client.force_authenticate(user=self.user)

        self.map = Map.objects.create(name="Dust2")

        self.weapon = Weapon.objects.create(
            name="AK-47", weapon_type=Weapon.WeaponType.RIFLE
        )

        self.match = Match.objects.create(
            map_played=self.map,
            created_by=self.user,
            result=Match.RESULT_CHOICES.WIN,
            team_score=13,
            opponent_score=10,
        )


# ------------------------
# USER REGISTER TEST
# ------------------------
class UserRegisterTest(APITestCase):
    def test_register_success(self):
        url = reverse("register")
        data = {
            "username": "newuser",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "email": "new@test.com",
            "rank": "Unranked",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_password_mismatch(self):
        url = reverse("register")
        data = {
            "username": "newuser",
            "password": "StrongPass123!",
            "password_confirm": "WrongPass",
            "email": "new@test.com",
            "rank": "Unranked",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ------------------------
# MATCH TESTS
# ------------------------
class MatchTest(BaseTestCase):
    def test_create_match(self):
        url = reverse("match-list")
        data = {
            "map_played": self.map.id,
            "result": "Win",
            "team_score": 13,
            "opponent_score": 5,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Match.objects.count(), 2)

    def test_user_only_sees_own_matches(self):
        Match.objects.create(
            map_played=self.map,
            created_by=self.other_user,
            result="Loss",
            team_score=5,
            opponent_score=13,
        )

        url = reverse("match-list")
        response = self.client.get(url)

        self.assertEqual(len(response.data["results"]), 1)


# ------------------------
# USER MATCH STAT TESTS
# ------------------------
class UserMatchStatTest(BaseTestCase):
    def test_create_valid_stat(self):
        url = reverse("match-stat-list")
        data = {
            "match": self.match.id,
            "kills": 20,
            "deaths": 10,
            "assists": 5,
            "mvp_rounds": 2,
            "score": 2500,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_negative_stats_fail(self):
        url = reverse("match-stat-list")
        data = {
            "match": self.match.id,
            "kills": -1,
            "deaths": 10,
            "assists": 5,
            "mvp_rounds": 2,
            "score": 2500,
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ------------------------
# WEAPON STAT TESTS
# ------------------------
class WeaponStatTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.stat = UserMatchStat.objects.create(
            user=self.user,
            match=self.match,
            kills=20,
            deaths=10,
            assists=5,
            mvp_rounds=2,
            score=2000,
        )

    def test_valid_weapon_stat(self):
        url = reverse("weapon-stat-list")
        data = {"stat": self.stat.id, "weapon": self.weapon.id, "kills": 10}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_weapon_kills_exceed_total(self):
        url = reverse("weapon-stat-list")

        WeaponStat.objects.create(stat=self.stat, weapon=self.weapon, kills=15)

        data = {
            "stat": self.stat.id,
            "weapon": self.weapon.id,
            "kills": 10,  # exceeds total (15 + 10 > 20)
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_weapon_kills(self):
        url = reverse("weapon-stat-list")
        data = {"stat": self.stat.id, "weapon": self.weapon.id, "kills": -5}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ------------------------
# USER STATS SUMMARY TEST
# ------------------------
class UserStatsSummaryTest(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.stat = UserMatchStat.objects.create(
            user=self.user,
            match=self.match,
            kills=20,
            deaths=10,
            assists=5,
            mvp_rounds=2,
            score=2000,
        )

        WeaponStat.objects.create(stat=self.stat, weapon=self.weapon, kills=15)

    def test_summary_endpoint(self):
        url = reverse("user-stats-summary-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data.get("results", [])) > 0)

        # Find the authenticated user's stats in results
        data = None
        for user_data in response.data["results"]:
            if user_data["id"] == self.user.id:
                data = user_data
                break

        self.assertIsNotNone(data, "Authenticated user not found in results")
        self.assertEqual(data["total_matches"], 1)
        self.assertEqual(data["favorite_weapon"], "AK-47")


# ==================== MODEL TESTS ====================
class UserModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="modeluser", email="model@example.com", password="testpass123"
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, "modeluser")
        self.assertEqual(self.user.email, "model@example.com")

    def test_user_rank_default(self):
        self.assertEqual(self.user.rank, User.RANK_CHOICES.UNRANKED)

    def test_user_rank_update(self):
        self.user.rank = User.RANK_CHOICES.GOLD
        self.user.save()
        self.user.refresh_from_db()
        self.assertEqual(self.user.rank, User.RANK_CHOICES.GOLD)

    def test_all_rank_choices(self):
        for rank_code, rank_name in User.RANK_CHOICES.choices:
            user = User.objects.create_user(
                username=f"user_{rank_code}", password="pass123"
            )
            user.rank = rank_code
            user.save()
            self.assertEqual(user.rank, rank_code)


class MapModelTests(TestCase):
    def test_map_creation(self):
        map_obj = Map.objects.create(name="Inferno")
        self.assertEqual(map_obj.name, "Inferno")
        self.assertEqual(str(map_obj), "Inferno")

    def test_multiple_maps(self):
        maps_data = ["Inferno", "Mirage", "Dust2", "Nuke", "Vertigo"]
        for map_name in maps_data:
            Map.objects.create(name=map_name)
        self.assertEqual(Map.objects.count(), 5)


class WeaponModelTests(TestCase):
    def test_weapon_creation(self):
        weapon = Weapon.objects.create(
            name="AK-47", weapon_type=Weapon.WeaponType.RIFLE
        )
        self.assertEqual(weapon.name, "AK-47")
        self.assertEqual(weapon.weapon_type, Weapon.WeaponType.RIFLE)

    def test_weapon_str_representation(self):
        weapon = Weapon.objects.create(
            name="AWP Dragons Lore", weapon_type=Weapon.WeaponType.SNIPER
        )
        self.assertEqual(str(weapon), "AWP Dragons Lore (Sniper)")

    def test_all_weapon_types(self):
        for weapon_type_code, weapon_type_name in Weapon.WeaponType.choices:
            weapon = Weapon.objects.create(
                name=f"Test {weapon_type_name}", weapon_type=weapon_type_code
            )
            self.assertEqual(weapon.weapon_type, weapon_type_code)


class MatchModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="matchuser", password="pass123")
        self.map = Map.objects.create(name="Inferno")

    def test_match_creation(self):
        match = Match.objects.create(
            map_played=self.map,
            created_by=self.user,
            result=Match.RESULT_CHOICES.WIN,
            team_score=13,
            opponent_score=11,
        )
        self.assertEqual(match.map_played, self.map)
        self.assertEqual(match.created_by, self.user)
        self.assertEqual(match.result, Match.RESULT_CHOICES.WIN)

    def test_match_score_boundaries(self):
        # Test minimum score
        match_min = Match.objects.create(
            map_played=self.map,
            created_by=self.user,
            result=Match.RESULT_CHOICES.LOSS,
            team_score=0,
            opponent_score=13,
        )
        self.assertEqual(match_min.team_score, 0)

        # Test maximum score
        match_max = Match.objects.create(
            map_played=self.map,
            created_by=self.user,
            result=Match.RESULT_CHOICES.WIN,
            team_score=13,
            opponent_score=0,
        )
        self.assertEqual(match_max.team_score, 13)

    def test_match_all_result_types(self):
        for result_code, result_name in Match.RESULT_CHOICES.choices:
            match = Match.objects.create(
                map_played=self.map,
                created_by=self.user,
                result=result_code,
                team_score=5,
                opponent_score=5,
            )
            self.assertEqual(match.result, result_code)


class UserMatchStatModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="statuser", password="pass123")
        self.map = Map.objects.create(name="Inferno")
        self.match = Match.objects.create(
            map_played=self.map,
            created_by=self.user,
            result=Match.RESULT_CHOICES.WIN,
            team_score=13,
            opponent_score=11,
        )

    def test_user_match_stat_creation(self):
        stat = UserMatchStat.objects.create(
            user=self.user,
            match=self.match,
            kills=20,
            deaths=5,
            assists=10,
            mvp_rounds=3,
            score=2500,
        )
        self.assertEqual(stat.kills, 20)
        self.assertEqual(stat.deaths, 5)

    def test_unique_together_constraint(self):
        UserMatchStat.objects.create(
            user=self.user, match=self.match, kills=20, deaths=5
        )

        with self.assertRaises(Exception):
            UserMatchStat.objects.create(
                user=self.user, match=self.match, kills=15, deaths=8
            )

    def test_stat_with_zero_values(self):
        stat = UserMatchStat.objects.create(
            user=self.user,
            match=self.match,
            kills=0,
            deaths=0,
            assists=0,
            mvp_rounds=0,
            score=0,
        )
        self.assertEqual(stat.kills, 0)


class WeaponStatModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="weaponuser", password="pass123")
        self.map = Map.objects.create(name="Inferno")
        self.match = Match.objects.create(
            map_played=self.map, created_by=self.user, result=Match.RESULT_CHOICES.WIN
        )
        self.stat = UserMatchStat.objects.create(
            user=self.user, match=self.match, kills=20
        )
        self.weapon = Weapon.objects.create(
            name="AK-47", weapon_type=Weapon.WeaponType.RIFLE
        )

    def test_weapon_stat_creation(self):
        weapon_stat = WeaponStat.objects.create(
            stat=self.stat, weapon=self.weapon, kills=10
        )
        self.assertEqual(weapon_stat.kills, 10)
        self.assertEqual(weapon_stat.stat, self.stat)
        self.assertEqual(weapon_stat.weapon, self.weapon)

    def test_weapon_stat_validation_exceeds_total(self):
        with self.assertRaises(Exception):
            weapon_stat = WeaponStat(
                stat=self.stat,
                weapon=self.weapon,
                kills=25,  # Exceeds match kills of 20
            )
            weapon_stat.save()

    def test_weapon_stat_multiple_weapons(self):
        ak_stat = WeaponStat.objects.create(
            stat=self.stat, weapon=self.weapon, kills=10
        )

        m4 = Weapon.objects.create(name="M4A1", weapon_type=Weapon.WeaponType.RIFLE)
        m4_stat = WeaponStat.objects.create(stat=self.stat, weapon=m4, kills=10)

        self.assertEqual(self.stat.weapon_stats.count(), 2)


# ==================== SERIALIZER TESTS ====================
class UserSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="serialuser",
            email="serial@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )

    def test_user_serializer_fields(self):
        serializer = UserSerializer(self.user)
        self.assertIn("id", serializer.data)
        self.assertIn("username", serializer.data)
        self.assertIn("email", serializer.data)
        self.assertIn("rank", serializer.data)
        self.assertEqual(serializer.data["username"], "serialuser")

    def test_user_serializer_rank_field(self):
        self.user.rank = User.RANK_CHOICES.GOLD
        self.user.save()
        serializer = UserSerializer(self.user)
        self.assertEqual(serializer.data["rank"], User.RANK_CHOICES.GOLD)


class MapSerializerTests(TestCase):
    def test_map_serializer(self):
        map_obj = Map.objects.create(name="Inferno")
        serializer = MapSerializer(map_obj)
        self.assertEqual(serializer.data["name"], "Inferno")

    def test_map_serializer_multiple_maps(self):
        maps = [Map.objects.create(name=name) for name in ["Mirage", "Dust2", "Nuke"]]
        serializer = MapSerializer(maps, many=True)
        self.assertEqual(len(serializer.data), 3)


class WeaponSerializerTests(TestCase):
    def test_weapon_serializer(self):
        weapon = Weapon.objects.create(
            name="AK-47", weapon_type=Weapon.WeaponType.RIFLE
        )
        serializer = WeaponSerializer(weapon)
        self.assertEqual(serializer.data["name"], "AK-47")
        self.assertEqual(serializer.data["weapon_type"], "Rifle")


class MatchSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="matchser", password="pass123")
        self.map = Map.objects.create(name="Inferno")
        self.match = Match.objects.create(
            map_played=self.map,
            created_by=self.user,
            result=Match.RESULT_CHOICES.WIN,
            team_score=13,
            opponent_score=11,
        )

    def test_match_serializer(self):
        serializer = MatchSerializer(self.match)
        self.assertEqual(serializer.data["result"], "Win")
        self.assertEqual(serializer.data["map_name"], "Inferno")
        self.assertEqual(serializer.data["team_score"], 13)

    def test_match_serializer_detail(self):
        stat = UserMatchStat.objects.create(user=self.user, match=self.match, kills=20)
        serializer = MatchSerializerDetail(self.match)
        self.assertEqual(serializer.data["map_name"], "Inferno")
        self.assertIn("user_stats", serializer.data)
        self.assertEqual(len(serializer.data["user_stats"]), 1)


class UserMatchStatSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="statser", password="pass123")
        self.map = Map.objects.create(name="Inferno")
        self.match = Match.objects.create(
            map_played=self.map, created_by=self.user, result=Match.RESULT_CHOICES.WIN
        )

    def test_user_match_stat_create_serializer_valid(self):
        data = {
            "match": self.match.id,
            "kills": 20,
            "deaths": 5,
            "assists": 10,
            "mvp_rounds": 3,
            "score": 2500,
        }
        serializer = UserMatchStatCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_user_match_stat_create_serializer_negative_kills(self):
        data = {
            "match": self.match.id,
            "kills": -5,
            "deaths": 5,
            "assists": 10,
            "mvp_rounds": 3,
            "score": 2500,
        }
        serializer = UserMatchStatCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_user_match_stat_create_serializer_all_negative(self):
        data = {
            "match": self.match.id,
            "kills": -5,
            "deaths": -5,
            "assists": -5,
            "mvp_rounds": -5,
            "score": -500,
        }
        serializer = UserMatchStatCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class WeaponStatSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="weaponser", password="pass123")
        self.map = Map.objects.create(name="Inferno")
        self.match = Match.objects.create(
            map_played=self.map, created_by=self.user, result=Match.RESULT_CHOICES.WIN
        )
        self.stat = UserMatchStat.objects.create(
            user=self.user, match=self.match, kills=20
        )
        self.weapon = Weapon.objects.create(
            name="AK-47", weapon_type=Weapon.WeaponType.RIFLE
        )

    def test_weapon_stat_create_serializer_valid(self):
        data = {"stat": self.stat.id, "weapon": self.weapon.id, "kills": 10}
        serializer = WeaponStatCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_weapon_stat_create_serializer_negative_kills(self):
        data = {"stat": self.stat.id, "weapon": self.weapon.id, "kills": -5}
        serializer = WeaponStatCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_weapon_stat_view_serializer(self):
        weapon_stat = WeaponStat.objects.create(
            stat=self.stat, weapon=self.weapon, kills=10
        )
        serializer = WeaponStatViewSerializer(weapon_stat)
        self.assertIn("weapon_name", serializer.data)
        self.assertEqual(serializer.data["weapon_name"], "AK-47")


# ==================== PERMISSION TESTS ====================
class IsAuthenticatedAndOwnerTests(TestCase):
    def setUp(self):
        self.permission = IsAuthenticatedAndOwner()
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username="permuser", password="pass123")
        self.staff_user = User.objects.create_user(
            username="permstaff", password="pass123", is_staff=True
        )

    def test_authenticated_owner_has_permission(self):
        request = self.factory.get("/")
        request.user = self.user

        view = type("View", (), {"action": "retrieve"})()

        self.assertTrue(self.permission.has_permission(request, view))
        self.assertTrue(self.permission.has_object_permission(request, view, self.user))

    def test_staff_has_permission(self):
        request = self.factory.get("/")
        request.user = self.staff_user

        view = type("View", (), {"action": "list"})()
        self.assertTrue(self.permission.has_permission(request, view))

    def test_unauthenticated_no_permission(self):
        request = self.factory.get("/")
        request.user = type("User", (), {"is_authenticated": False})()

        view = type("View", (), {"action": "retrieve"})()
        self.assertFalse(self.permission.has_permission(request, view))


class IsAuthenticatedOrReadOnlyTests(TestCase):
    def setUp(self):
        self.permission = IsAuthenticatedOrReadOnly()
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username="readuser", password="pass123")

    def test_get_request_allowed_anonymous(self):
        request = self.factory.get("/")
        request.user = type("User", (), {"is_authenticated": False})()

        view = type("View", (), {})()
        self.assertTrue(self.permission.has_permission(request, view))

    def test_post_request_authenticated(self):
        request = self.factory.post("/")
        request.user = self.user

        view = type("View", (), {})()
        self.assertTrue(self.permission.has_permission(request, view))

    def test_post_request_anonymous_denied(self):
        request = self.factory.post("/")
        request.user = type("User", (), {"is_authenticated": False})()

        view = type("View", (), {})()
        self.assertFalse(self.permission.has_permission(request, view))

    def test_put_request_anonymous_denied(self):
        request = self.factory.put("/")
        request.user = type("User", (), {"is_authenticated": False})()

        view = type("View", (), {})()
        self.assertFalse(self.permission.has_permission(request, view))


# ==================== API ENDPOINT TESTS ====================
class UserMatchViewSetTests(BaseTestCase):
    def test_create_match_success(self):
        url = reverse("match-list")
        data = {
            "map_played": self.map.id,
            "result": "Win",
            "team_score": 13,
            "opponent_score": 5,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Match.objects.count(), 2)

    def test_user_only_sees_own_matches(self):
        Match.objects.create(
            map_played=self.map,
            created_by=self.other_user,
            result="Loss",
            team_score=5,
            opponent_score=13,
        )
        url = reverse("match-list")
        response = self.client.get(url)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_staff_sees_all_matches(self):
        self.client.force_authenticate(user=self.staff_user)
        Match.objects.create(
            map_played=self.map,
            created_by=self.other_user,
            result="Loss",
            team_score=5,
            opponent_score=13,
        )
        url = reverse("match-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_retrieve_match_detail(self):
        url = reverse("match-detail", kwargs={"pk": self.match.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["team_score"], 13)

    def test_create_match_without_auth_fails(self):
        client = APIClient()
        url = reverse("match-list")
        data = {
            "map_played": self.map.id,
            "result": "Win",
            "team_score": 13,
            "opponent_score": 5,
        }
        response = client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserMatchStatViewSetTests(BaseTestCase):
    def test_create_valid_stat(self):
        url = reverse("match-stat-list")
        data = {
            "match": self.match.id,
            "kills": 20,
            "deaths": 10,
            "assists": 5,
            "mvp_rounds": 2,
            "score": 2500,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_negative_stats_fail(self):
        url = reverse("match-stat-list")
        data = {
            "match": self.match.id,
            "kills": -1,
            "deaths": 10,
            "assists": 5,
            "mvp_rounds": 2,
            "score": 2500,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_stat_detail(self):
        stat = UserMatchStat.objects.create(
            user=self.user, match=self.match, kills=20, deaths=5
        )
        url = reverse("match-stat-detail", kwargs={"pk": stat.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["kills"], 20)
        self.assertIn("weapon_stats", response.data)

    def test_all_negative_stats_fail(self):
        url = reverse("match-stat-list")
        data = {
            "match": self.match.id,
            "kills": -5,
            "deaths": -10,
            "assists": -5,
            "mvp_rounds": -2,
            "score": -2500,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class WeaponStatViewSetTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.stat = UserMatchStat.objects.create(
            user=self.user,
            match=self.match,
            kills=20,
            deaths=10,
            assists=5,
            mvp_rounds=2,
            score=2000,
        )

    def test_valid_weapon_stat(self):
        url = reverse("weapon-stat-list")
        data = {"stat": self.stat.id, "weapon": self.weapon.id, "kills": 10}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_weapon_kills_exceed_total(self):
        url = reverse("weapon-stat-list")

        WeaponStat.objects.create(stat=self.stat, weapon=self.weapon, kills=15)

        data = {
            "stat": self.stat.id,
            "weapon": self.weapon.id,
            "kills": 10,  # 15 + 10 > 20 (exceeds total)
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_negative_weapon_kills(self):
        url = reverse("weapon-stat-list")
        data = {"stat": self.stat.id, "weapon": self.weapon.id, "kills": -5}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_weapon_stats(self):
        WeaponStat.objects.create(stat=self.stat, weapon=self.weapon, kills=10)
        url = reverse("weapon-stat-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_only_sees_own_weapon_stats(self):
        WeaponStat.objects.create(stat=self.stat, weapon=self.weapon, kills=10)

        # Create another user's stat
        other_stat = UserMatchStat.objects.create(
            user=self.other_user, match=self.match, kills=15
        )
        WeaponStat.objects.create(stat=other_stat, weapon=self.weapon, kills=10)

        url = reverse("weapon-stat-list")
        response = self.client.get(url)
        self.assertEqual(len(response.data["results"]), 1)


class MapViewSetTests(APITestCase):
    def setUp(self):
        self.map1 = Map.objects.create(name="Inferno")
        self.map2 = Map.objects.create(name="Mirage")
        self.client = APIClient()

    def test_list_maps(self):
        url = reverse("map-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_retrieve_map(self):
        url = reverse("map-detail", kwargs={"pk": self.map1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Inferno")

    def test_cannot_create_map_unauthenticated(self):
        url = reverse("map-list")
        data = {"name": "NewMap"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class WeaponViewSetTests(APITestCase):
    def setUp(self):
        self.weapon1 = Weapon.objects.create(
            name="AK-47", weapon_type=Weapon.WeaponType.RIFLE
        )
        self.weapon2 = Weapon.objects.create(
            name="AWP", weapon_type=Weapon.WeaponType.SNIPER
        )
        self.client = APIClient()

    def test_list_weapons(self):
        url = reverse("weapon-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_retrieve_weapon(self):
        url = reverse("weapon-detail", kwargs={"pk": self.weapon1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "AK-47")

    def test_cannot_create_weapon_unauthenticated(self):
        url = reverse("weapon-list")
        data = {"name": "New Weapon", "weapon_type": "Rifle"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
