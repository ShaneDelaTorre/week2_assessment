from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum

# Create your models here.
class User(AbstractUser):
    class RANK_CHOICES(models.TextChoices):
        UNRANKED = 'Unranked'
        SILVER = 'Below 5000'
        LIGHT_BLUE = '5000-9999'
        DARK_BLUE = '10000-14999'
        LIGHT_PURPLE = '15000-19999'
        DARK_PURPLE = '20000-24999'
        RED = '25000-29999'
        GOLD = '30000+'

    rank = models.CharField(max_length=30, choices=RANK_CHOICES.choices, default=RANK_CHOICES.UNRANKED)

    def __str__(self):
        return self.username
    @property
    def total_matches(self):
        return self.matches.count()
    @property
    def win_rate(self):
        total = self.total_matches
        if total == 0:
            return 0
        wins = self.matches.filter(result=Match.RESULT_CHOICES.WIN).count()
        return (wins / total) * 100
    @property
    def win_rate_by_map(self):
        maps = Map.objects.all()
        win_rates = {}
        for match_map in maps:
            matches_on_map = self.matches.filter(map_played=match_map)
            total = matches_on_map.count()
            if total == 0:
                win_rates[match_map.name] = 0
            else:
                wins = matches_on_map.filter(result=Match.RESULT_CHOICES.WIN).count()
                win_rates[match_map.name] = (wins / total) * 100
        return win_rates
    @property
    def favorite_weapon(self):
        weapon_stats = WeaponStat.objects.filter(stat__user=self)
        if not weapon_stats.exists():
            return None
        favorite = weapon_stats.order_by('-kills').first()
        return favorite.weapon.name
    @property
    def kill_death_ratio(self):
        stats = UserMatchStat.objects.filter(user=self)
        total_kills = sum(stat.kills for stat in stats)
        total_deaths = sum(stat.deaths for stat in stats)
        if total_deaths == 0:
            return total_kills
        return f"{total_kills / total_deaths:.2f}/KDR"
    
class Map(models.Model):
    name = models.CharField(max_length=64)

    def __str__(self):
        return self.name

class Match(models.Model):
    class RESULT_CHOICES(models.TextChoices):
        WIN = 'Win'
        LOSS = 'Loss'
        DRAW = 'Draw'

    map_played = models.ForeignKey(Map, on_delete=models.CASCADE, related_name='map_played')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='matches')
    date_played = models.DateTimeField(auto_now_add=True)
    result = models.CharField(max_length=10, choices=RESULT_CHOICES.choices)
    team_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(13)])
    opponent_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(13)])

    def __str__(self):
        return f"{self.created_by.username} - {self.map_played.name} - ({self.team_score} - {self.opponent_score}) on {self.date_played.strftime('%Y-%m-%d %H:%M:%S')}"


class UserMatchStat(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='match_stats')
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='user_stats')
    kills = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    deaths = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    assists = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    mvp_rounds = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    score = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    class Meta:
        unique_together = ('user', 'match')

    def __str__(self):
        return f"{self.user.username} - {self.match.map_played.name} - ({self.match.team_score} - {self.match.opponent_score}) on {self.match.date_played.strftime('%Y-%m-%d %H:%M:%S')}"
    
class Weapon(models.Model):
    class WeaponType(models.TextChoices):
        RIFLE = 'Rifle'
        SMG = 'SMG'
        SHOTGUN = 'Shotgun'
        SNIPER = 'Sniper'
        MELEE = 'Melee'
        PISTOL = 'Pistol'
        MACHINE_GUN = 'Machine Gun'

    name = models.CharField(max_length=64)
    weapon_type = models.CharField(max_length=20, choices=WeaponType.choices)

    def __str__(self):
        return f"{self.name} ({self.weapon_type})"
    
class WeaponStat(models.Model):
    stat = models.ForeignKey(UserMatchStat, on_delete=models.CASCADE, related_name='weapon_stats')
    weapon = models.ForeignKey(Weapon, on_delete=models.CASCADE, related_name='weapon_stats')
    kills = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ('stat', 'weapon')

    def __str__(self):
        return f"{self.stat.user.username} - {self.weapon.name} in {self.stat.match.map_played.name} ({self.stat.match.team_score} - {self.stat.match.opponent_score}): {self.kills} kills"
    
    def save(self, *args, **kwargs):
        existing_sum = self.stat.weapon_stats.exclude(pk=self.pk).aggregate(total=Sum('kills'))['total'] or 0
        if existing_sum + self.kills > self.stat.kills:
            raise ValidationError("Total weapon kills cannot exceed the total kills in the match.")
        super().save(*args, **kwargs)