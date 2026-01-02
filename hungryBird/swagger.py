from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
    openapi.Info(
        title="Hungry Bird API",
        default_version='v1',
        description="""
        API documentation for Hungry Bird Food Delivery Application
        
        ## 🔌 WebSocket Endpoints (Real-time Updates)

        ### Driver Notifications
        **URL:** `ws://<host>/ws/driver/{driver_id}/`  
        **Purpose:** Receive delivery requests and pickup/drop details  
        **Message Types:**
        - `delivery.request`

        **Sample Message:**
        ```json
        {
        "type": "delivery_request",
        "order_id": 12,
        "pickup": { "pick_lat": 23.77, "pick_lng": 90.41 },
        "dropoff": { "delivery_lat": 23.75, "delivery_lng": 90.39 }
        }
        """,
        terms_of_servie="http://www.google.com/policies/terms",
        contact=openapi.Contact(email="contact@myapi.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)