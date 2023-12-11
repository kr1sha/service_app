from django.conf import settings
from django.db.models import Prefetch, F, Sum
from django.shortcuts import render
from rest_framework.viewsets import ReadOnlyModelViewSet
from django.core.cache import cache

from clients.models import Client
from services.models import Subscription, Plan
from services.serializers import SubscriptionSerializer
from services.tasks import get_total_price


class SubscriptionView(ReadOnlyModelViewSet):
    queryset = Subscription.objects.all().prefetch_related(
        Prefetch('client', queryset=Client.objects.all().select_related('user').only(
            'company_name', 'user__email')),
        'plan'
    )
        #.annotate(price=F('service__full_price') * (100.0 - F('plan__discount_percent')) / 100)
    serializer_class = SubscriptionSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        response = super().list(request, *args, **kwargs)

        total_price = get_total_price(queryset)

        response_data = {'result': response.data}
        response_data['total_amount'] = total_price
        response.data = response_data

        return response




