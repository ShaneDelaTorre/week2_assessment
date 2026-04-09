from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterUserAPIView.as_view(), name="register"),
]

router = DefaultRouter()
router.register("users", views.UserViewSet, basename="user")
router.register(
    "user-stats-summary", views.UserStatsSummaryViewSet, basename="user-stats-summary"
)
router.register("user-matches", views.UserMatchViewSet, basename="match")
router.register("match-stats", views.UserMatchStatViewSet, basename="match-stat")
router.register("weapon-stats", views.WeaponStatViewSet, basename="weapon-stat")
router.register("maps", views.MapViewSet, basename="map")
router.register("weapons", views.WeaponViewSet, basename="weapon")
urlpatterns += router.urls
