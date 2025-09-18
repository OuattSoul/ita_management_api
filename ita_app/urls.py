from rest_framework.routers import DefaultRouter
from .views import PresenceViewSet,LeaveViewSet,UserViewSet,EmployeeViewSet,RecruitmentRequestViewSet,JobTitleViewSet,EmployeeAttendanceViewSet,MissionViewSet

router = DefaultRouter()
router.register(r'api/users', UserViewSet, basename='user')
router.register(r'api/employees', EmployeeViewSet, basename='employee')
router.register(r'api/recruitments', RecruitmentRequestViewSet, basename='recruitment')
router.register(r'api/jobs', JobTitleViewSet, basename='job-title')
router.register(r'api/employee_attendance', EmployeeAttendanceViewSet, basename='attendance') # leave it
router.register(r'api/missions', MissionViewSet, basename='missions')
router.register(r'api/leaves', LeaveViewSet, basename='leave')
router.register(r'api/presences', PresenceViewSet, basename='presence')


urlpatterns = router.urls
