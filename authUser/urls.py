from django.urls import path
from .views import *


urlpatterns = [
    path('roles/', get_role_choices, name='get_role_choices'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('details/', UserQueryView.as_view(), name='details')
]