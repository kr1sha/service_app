import datetime
import time

from celery import shared_task
from celery_singleton import Singleton
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Sum
from django.db.models.query import QuerySet


@shared_task(base=Singleton)
def set_price(subscription_id: int) -> None:
    """recalculate and rewrite price for Subscription with this subscription_id (price depends
     on service and plan discount)"""
    from services.models import Subscription

    with transaction.atomic(): # запрещает второму таску брать эти данные, пока этот не закончится
# чтоб он там ничего не перезаписал, а мы не поменяли обратно, записав наши старые данные select_for_update()
        time.sleep(5)

        #subscription = Subscription.objects.get(id=subscription_id)
        #new_price = (subscription.service.full_price * (100.0 - subscription.plan.discount_percent) / 100)
        subscription = Subscription.objects.select_for_update().filter(id=subscription_id).annotate(
            annotated_price=F('service__full_price') * (100.0 - F('plan__discount_percent')) / 100).first()
        subscription.price = subscription.annotated_price
        subscription.save()
    cache.delete(settings.PRICE_CACHE_NAME)


def set_all_subscriptions_prices() -> None:
    """recalculate and rewrite price for all existing Subscriptions (price depends
     on service and plan discount)"""
    from services.models import Subscription

    for subscription in Subscription.objects.all():
        set_price.delay(subscription.id)


def get_total_price(subscription_queryset: QuerySet) -> int:
    """get aggregated sum of all Subscriptions prices (and cached it)"""
    price_cache = cache.get(settings.PRICE_CACHE_NAME)

    if price_cache:
        total_price = price_cache
    else:
        total_price = subscription_queryset.aggregate(total=Sum('price')).get('total')
        cache.set(settings.PRICE_CACHE_NAME, total_price, 60 * 60)

    return total_price


