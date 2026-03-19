from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/optimizer/', include('optimizer.urls')),
]



def healthz(_): return HttpResponse("ok", content_type="text/plain")
urlpatterns += [ path("healthz", healthz) ]