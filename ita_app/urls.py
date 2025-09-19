from rest_framework.routers import DefaultRouter
from .views import MemoViewSet,CategoryViewSet,PurchaseRequestViewSet,VehiculeViewSet,JobTypeViewSet,UserRoleViewSet,PresenceViewSet,LeaveViewSet,UserViewSet,EmployeeViewSet,RecruitmentRequestViewSet,JobTitleViewSet,EmployeeAttendanceViewSet,MissionViewSet

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
router.register(r'api/job/titles', JobTypeViewSet, basename='job_titles')
router.register(r"api/vehicules", VehiculeViewSet, basename="vehicule")
router.register(r'api/purchase/categories', CategoryViewSet, basename='category')
router.register(r'api/purchase/requests', PurchaseRequestViewSet, basename='purchase_request')
router.register(r'api/memo', MemoViewSet, basename='memo')

urlpatterns = router.urls
