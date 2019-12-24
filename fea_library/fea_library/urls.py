"""fea_library URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
# serve用来渲染媒体文件
from django.views.static import serve
from django.conf import settings


from app_web import views as web_view


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^login/$', web_view.LoginView.as_view()),
    url(r'^home/$', web_view.HomeView.as_view()),
    url(r'^logout/$', web_view.LogoutView.as_view()),
    url(r'^read_main/$', web_view.ReadMain.as_view()),
    url(r'^set_fatigue/$', web_view.SetFatigue.as_view()),
    url(r'^show_progress_read/$', web_view.ShowProgressReading.as_view()),
    url(r'^show_progress_process/$', web_view.ShowProgressProcessing.as_view()),
    url(r'^create_python/$', web_view.GenerateInput.as_view()),
    url(r'^show_log/$', web_view.ShowLog.as_view()),
    url(r'^start_process/$', web_view.StartProcess.as_view()),






    url(r'^media/(?P<path>.*)', serve, {'document_root': settings.MEDIA_ROOT}),
]
