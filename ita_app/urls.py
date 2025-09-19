from rest_framework.routers import DefaultRouter
from .views import UserRoleViewSet,PresenceViewSet,LeaveViewSet,UserViewSet,EmployeeViewSet,RecruitmentRequestViewSet,JobTitleViewSet,EmployeeAttendanceViewSet,MissionViewSet

router = DefaultRouter()
router.register(r'api/users', UserViewSet, basename='user')
router.register(r'api/employees', EmployeeViewSet, basename='employee')
router.register(r'api/recruitments', RecruitmentRequestViewSet, basename='recruitment')
router.register(r'api/jobs', JobTitleViewSet, basename='job-title')
router.register(r'api/employee_attendance', EmployeeAttendanceViewSet, basename='attendance') # leave it
router.register(r'api/missions', MissionViewSet, basename='missions')
router.register(r'api/leaves', LeaveViewSet, basename='leave')
router.register(r'api/attendances', PresenceViewSet, basename='presence')
router.register(r'api/roles', UserRoleViewSet, basename='user_roles')
router.register(r'api/job/types', JobTitleViewSet, basename='job_types')
router.register(r'api/job/titles', JobTitleViewSet, basename='job_titles')

urlpatterns = router.urls
