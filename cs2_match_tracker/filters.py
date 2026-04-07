import django_filters
from .models import Match

class MatchFilter(django_filters.FilterSet):
    map_played = django_filters.CharFilter(field_name='map_played__name', lookup_expr='icontains')
    date_played = django_filters.DateFromToRangeFilter()
    result = django_filters.CharFilter(field_name='result', lookup_expr='iexact')

    class Meta:
        model = Match
        fields = ['map_played', 'date_played', 'result']