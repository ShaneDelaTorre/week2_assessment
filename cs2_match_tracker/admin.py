from django.contrib import admin

from .models import Map, Match, User, UserMatchStat, Weapon, WeaponStat

# Register your models here.
admin.site.register(User)
admin.site.register(Map)
admin.site.register(Match)
admin.site.register(UserMatchStat)
admin.site.register(Weapon)
admin.site.register(WeaponStat)
