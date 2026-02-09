from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .swagger import schema_view
from payment.views import subscription_webhook_handler


urlpatterns = [
    path('admin/', admin.site.urls),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/authUser/', include('authUser.urls')),
    path('api/v1/cart/', include('cart.urls')),
    path('api/v1/', include('restaurant.urls')),
    path('api/v1/', include('order.urls')),
    path('api/v1/driver/', include('driver.urls')),
    path('api/v1/', include('review.urls')),
    path('api/v1/subscriptions/', include('subscriptions.urls')),
    path('api/v1/payment/webhooks/subscription/', subscription_webhook_handler, name='subscription-webhook'),
    path('api/v1/dashboard/', include('dashboard.urls')),
    path('api/v1/recommendations/', include('recommendations.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
