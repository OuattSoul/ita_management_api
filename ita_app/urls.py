from rest_framework.routers import DefaultRouter
from .views import UserViewSet,EmployeeViewSet,RecruitmentRequestViewSet

router = DefaultRouter()
router.register(r'api/users', UserViewSet, basename='user')
router.register(r'api/employees', EmployeeViewSet, basename='employee')
router.register(r'api/recruitments', RecruitmentRequestViewSet, basename='recruitment')


urlpatterns = router.urls
