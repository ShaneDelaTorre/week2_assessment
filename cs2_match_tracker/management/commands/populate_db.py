import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from cs2_match_tracker.models import Map, Match, User, UserMatchStat, Weapon, WeaponStat


class Command(BaseCommand):
    help = "Populate users, matches, and stats (no map/weapon creation)"

    def handle(self, *args, **options):

        # --- Fetch existing maps & weapons ---
        maps = list(Map.objects.all())
        weapons = list(Weapon.objects.all())

        if not maps or not weapons:
            self.stdout.write(
                self.style.ERROR(
                    "❌ You must have existing Maps and Weapons in DB first."
                )
            )
            return

        # --- Create Users ---
        ranks = [r.value for r in User.RANK_CHOICES]
        users = []

        for _ in range(10):
            username = f"user_{random.randint(1000, 9999)}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "rank": random.choice(ranks),
                },
            )
            if created:
                user.set_password("Password123!")
                user.save()

            users.append(user)

        self.stdout.write(f"✅ Created {len(users)} users")

        # --- Create Matches ---
        for _ in range(20):
            match_creator = random.choice(users)
            match = Match.objects.create(
                map_played=random.choice(maps),
                created_by=match_creator,
                date_played=timezone.now(),
                result=random.choice(
                    [
                        Match.RESULT_CHOICES.WIN,
                        Match.RESULT_CHOICES.LOSS,
                        Match.RESULT_CHOICES.DRAW,
                    ]
                ),
                team_score=random.randint(0, 13),
                opponent_score=random.randint(0, 13),
            )

            # --- Create stats only for the user who created the match ---
            kills = random.randint(0, 25)
            deaths = random.randint(0, 25)
            assists = random.randint(0, 10)
            mvp_rounds = random.randint(0, 5)
            score = kills * 100 + assists * 50

            stat = UserMatchStat.objects.create(
                user=match_creator,
                match=match,
                kills=kills,
                deaths=deaths,
                assists=assists,
                mvp_rounds=mvp_rounds,
                score=score,
            )

            # --- WeaponStats (respect total kills constraint) ---
            remaining_kills = kills

            # Pick random subset of weapons
            selected_weapons = random.sample(
                weapons, k=min(len(weapons), random.randint(1, 4))
            )

            for weapon in selected_weapons[:-1]:
                if remaining_kills <= 0:
                    break

                w_kills = random.randint(0, remaining_kills)
                WeaponStat.objects.create(stat=stat, weapon=weapon, kills=w_kills)
                remaining_kills -= w_kills

            # Last weapon gets remaining kills
            if remaining_kills > 0:
                WeaponStat.objects.create(
                    stat=stat, weapon=selected_weapons[-1], kills=remaining_kills
                )

        self.stdout.write(self.style.SUCCESS("🔥 Database populated successfully!"))
