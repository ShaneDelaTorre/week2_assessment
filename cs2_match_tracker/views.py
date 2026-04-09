from django.db.models import Prefetch
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .filters import MatchFilter
from .models import Map, Match, User, UserMatchStat, Weapon, WeaponStat
from .permissions import IsAuthenticatedAndOwner, IsAuthenticatedOrReadOnly
from .serializers import (
    MapSerializer,
    MatchSerializer,
    MatchSerializerDetail,
    UserMatchStatCreateSerializer,
    UserMatchStatDetailSerializer,
    UserRegisterSerializer,
    UserSerializer,
    UserStatsSummarySerializer,
    WeaponSerializer,
    WeaponStatCreateSerializer,
    WeaponStatViewSerializer,
)


class RegisterUserAPIView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = [AllowAny]


class UserViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedAndOwner]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=["get", "put", "patch", "delete"], url_path="me")
    def me(self, request):
        user = request.user
        if request.method == "GET":
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        if request.method in ["PUT", "PATCH"]:
            serializer = self.get_serializer(
                user, data=request.data, partial=(request.method == "PATCH")
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        if request.method == "DELETE":
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class UserStatsSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserStatsSummarySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.prefetch_related(
            Prefetch("matches", queryset=Match.objects.select_related("map_played")),
            "match_stats__weapon_stats__weapon",
        )


class UserMatchViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_class = MatchFilter

    def get_queryset(self):
        user = self.request.user
        queryset = Match.objects.select_related("map_played").prefetch_related(
            "user_stats__weapon_stats__weapon"
        )
        if user.is_staff:
            return queryset
        return queryset.filter(created_by=user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MatchSerializerDetail
        return MatchSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        return serializer.data


class UserMatchStatViewSet(viewsets.ModelViewSet):
    queryset = UserMatchStat.objects.select_related("user", "match").prefetch_related(
        "weapon_stats__weapon"
    )
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return UserMatchStatDetailSerializer
        return UserMatchStatCreateSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(user=user)


class WeaponStatViewSet(viewsets.ModelViewSet):
    queryset = WeaponStat.objects.select_related("stat__user", "stat__match", "weapon")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return WeaponStatCreateSerializer
        return WeaponStatViewSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return self.queryset
        return self.queryset.filter(stat__user=user)


class MapViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Map.objects.all()
    serializer_class = MapSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class WeaponViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Weapon.objects.all()
    serializer_class = WeaponSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
