"""
URL configuration for ita_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from ita_app.views import create_employee,presence_pointage,get_pointage,get_employees,db_connectivity,get_staff,assign_mission,get_missions,set_leaves,get_leaves,request_recruitment,get_recruitments, get_users_query, register_staff, login_staff

urlpatterns = [
    path('admin/', admin.site.urls),
    path("db-health/", db_connectivity, name="db_health"),
    path("get-users/", get_users_query, name="get-users"),
    path("api/staff/register/", register_staff, name="register-staff"),
    path("api/staff/login/", login_staff, name="login-staff"),
    path("api/staff/list/", get_staff, name="get-users"),
    path("api/missions/assign/", assign_mission, name="assign-mission"),
    path("api/missions/get-mission/", get_missions, name="get-mission"),
    path("api/leaves/set-leave/", set_leaves, name="set-leave"),
    path("api/leaves/get-leave/", get_leaves, name="get-leave"),
    path("api/recruitments/request/", request_recruitment, name="request-recruitment"),
    path("api/recruitments/get-recruitments/", get_recruitments, name="get-recruitments"),
    path("api/employees/create/", create_employee, name="create-employee"),
    path("api/employees/list/", get_employees, name="get-employees"),
    path("api/employees/set-pointage/", presence_pointage, name="set-presence"),
    path("api/employees/pointage/", get_pointage, name="get-presence"),
]
