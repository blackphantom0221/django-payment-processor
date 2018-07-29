from django.contrib import admin
from django.urls import re_path, include
from orders.views import HomeView, OrderView

app_name = 'getpaid_example'

urlpatterns = [
    re_path(r'^admin/', admin.site.urls),

    re_path(r'^$', HomeView.as_view(), name='home'),
    re_path(r'^order/(?P<pk>\d+)/$', OrderView.as_view(), name='order_detail'),
    re_path(r'^payments/', include('getpaid.urls')),
]