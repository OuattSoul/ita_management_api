from rest_framework.routers import DefaultRouter
from .views import UserViewSet,EmployeeViewSet

router = DefaultRouter()
router.register(r'api/users', UserViewSet, basename='user')
router.register(r'api/employees', EmployeeViewSet, basename='employee')

urlpatterns = router.urls
