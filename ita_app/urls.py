from rest_framework.routers import DefaultRouter
from .views import UserViewSet,EmployeeViewSet,RecruitmentRequestViewSet,JobTitleViewSet

router = DefaultRouter()
router.register(r'api/users', UserViewSet, basename='user')
router.register(r'api/employees', EmployeeViewSet, basename='employee')
router.register(r'api/recruitments', RecruitmentRequestViewSet, basename='recruitment')
router.register(r'jobs', JobTitleViewSet, basename='job-title')


urlpatterns = router.urls
