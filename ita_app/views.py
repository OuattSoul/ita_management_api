# views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import connection
from django.db.utils import IntegrityError
import datetime

class UserViewSet(viewsets.ViewSet):
    """
    ViewSet DRF pour gérer les utilisateurs via SQL direct.
    """

    def list(self, request):
        """GET /users/ → récupérer tous les utilisateurs"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, user_role_id, user_id, email_prof, job_title_id,
                           affected_at_service_id, hire_date, job_type_id, profile_status,
                           created_at, updated_at
                    FROM users
                    ORDER BY id;
                """)
                rows = cursor.fetchall()
                users = []
                for row in rows:
                    users.append({
                        "id": row[0],
                        "user_role_id": row[1],
                        "user_id": row[2],
                        "email_prof": row[3],
                        "job_title_id": row[4],
                        "affected_at_service_id": row[5],
                        "hire_date": row[6],
                        "job_type_id": row[7],
                        "profile_status": row[8],
                        "created_at": row[9],
                        "updated_at": row[10],
                    })
            return Response({"status": "success", "users": users})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """POST /users/ → créer un nouvel utilisateur"""
        data = request.data
        try:
            user_role_id = data.get("user_role_id")
            user_id = data.get("user_id")
            email_prof = data.get("email_prof")
            job_title_id = data.get("job_title_id")
            affected_at_service_id = data.get("affected_at_service_id")
            hire_date = data.get("hire_date")
            job_type_id = data.get("job_type_id")
            profile_status = data.get("profile_status", "incomplet")

            created_at = datetime.datetime.now()
            updated_at = datetime.datetime.now()

            required_fields = [user_role_id, user_id, email_prof, job_title_id,
                               affected_at_service_id, hire_date, job_type_id]
            if not all(required_fields):
                return Response(
                    {"status": "error", "message": "Tous les champs obligatoires doivent être remplis"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO users
                    (user_role_id, user_id, email_prof, job_title_id, affected_at_service_id,
                     hire_date, job_type_id, profile_status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, [
                    user_role_id, user_id, email_prof, job_title_id,
                    affected_at_service_id, hire_date, job_type_id, profile_status,
                    created_at, updated_at
                ])
                row = cursor.fetchone()
                if not row:
                    return Response(
                        {"status": "error", "message": "L'utilisateur n'a pas pu être créé"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                user_id_created = row[0]

            return Response({
                "status": "success",
                "message": "Utilisateur créé avec succès",
                "user_id": user_id_created
            }, status=status.HTTP_201_CREATED)

        except IntegrityError as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
