# views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import connection
from django.db.utils import IntegrityError
from django.contrib.auth.hashers import make_password
import datetime, resend, requests, random

def generate_access_code():
    """Génère un code d'accès unique à 4 chiffres."""
    return str(random.randint(1000, 9999))

def unplunk_send_email(user_name, user_email, access_code):
    requests.post(
        "https://api.useplunk.com/v1/send",
        headers={"Content-Type": "application/json", "Authorization": "Bearer sk_e018919f0784429c320ea75de1a997e4e665a39395160a5c"},
        json={
        "subject": "Création de compte",
        #"body": "Hello from Plunk!", 
        "body": f"Bonjour {user_name}, <br/><br/>Votre code d\'accès est le suivant : <strong>{access_code}</strong>.<strong>Ne le communiquez à personne</strong>.",
        "to": f"{user_email}", 
        },
    )

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

    def retrieve(self, request, pk=None):
        """GET /users/{id}/ → récupérer un utilisateur"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, user_role_id, user_id, email_prof, employee_function_id,
                           affected_at_service_id, hire_date, job_type_id, profile_status,
                           created_at, updated_at
                    FROM users
                    WHERE id = %s;
                """, [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Utilisateur non trouvé"}, status=status.HTTP_404_NOT_FOUND)

                user = {
                    "id": row[0],
                    "user_role_id": row[1],
                    "user_id": row[2],
                    "email_prof": row[3],
                    "employee_function_id": row[4],
                    "affected_at_service_id": row[5],
                    "hire_date": row[6],
                    "job_type_id": row[7],
                    "profile_status": row[8],
                    "created_at": row[9],
                    "updated_at": row[10],
                }
            return Response({"status": "success", "user": user})
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

            while True:
                code = generate_access_code() # encrypt this code
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM staffs WHERE access_code = %s", [code])
                    exists = cursor.fetchone()
                if not exists:
                    access_code = code
                    break

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

    def update(self, request, pk=None):
        """PUT /users/{id}/ → mettre à jour un utilisateur (toutes les colonnes)"""
        data = request.data
        try:
            updated_at = datetime.datetime.now()
            fields = ["user_role_id", "user_id", "email_prof", "employee_function_id",
                      "affected_at_service_id", "hire_date", "job_type_id", "profile_status"]
            values = [data.get(f) for f in fields]

            if not all(values):
                return Response({"status": "error", "message": "Tous les champs doivent être fournis pour PUT"},
                                status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE users
                    SET user_role_id=%s, user_id=%s, email_prof=%s, employee_function_id=%s,
                        affected_at_service_id=%s, hire_date=%s, job_type_id=%s, profile_status=%s,
                        updated_at=%s
                    WHERE id=%s
                    RETURNING id;
                """, values + [updated_at, pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Utilisateur non trouvé"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Utilisateur mis à jour", "user_id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, pk=None):
        """PATCH /users/{id}/ → mise à jour partielle"""
        data = request.data
        try:
            updated_at = datetime.datetime.now()
            set_clauses = []
            values = []
            for key, val in data.items():
                if key in ["user_role_id", "user_id", "email_prof", "employee_function_id",
                           "affected_at_service_id", "hire_date", "job_type_id", "profile_status"]:
                    set_clauses.append(f"{key}=%s")
                    values.append(val)
            if not set_clauses:
                return Response({"status": "error", "message": "Aucun champ valide fourni"}, status=status.HTTP_400_BAD_REQUEST)

            set_clauses.append("updated_at=%s")
            values.append(updated_at)
            values.append(pk)

            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE users
                    SET {', '.join(set_clauses)}
                    WHERE id=%s
                    RETURNING id;
                """, values)
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Utilisateur non trouvé"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Utilisateur mis à jour partiellement", "user_id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """DELETE /users/{id}/ → supprimer un utilisateur"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE id=%s RETURNING id;", [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Utilisateur non trouvé"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"status": "success", "message": "Utilisateur supprimé", "user_id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeeViewSet(viewsets.ViewSet):
    """
    ViewSet CRUD complet pour la table 'employees' via SQL direct.
    """

    def list(self, request):
        """GET /employees/ → récupérer tous les employés"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, matricule, full_name, job_title_id, service_id, hire_date,
                           created_at, updated_at, profil_status
                    FROM employees
                    ORDER BY id;
                """)
                rows = cursor.fetchall()
                employees = []
                for row in rows:
                    employees.append({
                        "id": row[0],
                        "matricule": row[1],
                        "full_name": row[2],
                        "job_title_id": row[3],
                        "service_id": row[4],
                        "hire_date": row[5],
                        "created_at": row[6],
                        "updated_at": row[7],
                        "profil_status" : row[8]
                    })
            return Response({"status": "success", "employees": employees})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """GET /employees/{id}/ → récupérer un employé"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, matricule, full_name, job_title_id, service_id, hire_date,
                           created_at, updated_at,profil_status
                    FROM employees
                    WHERE id = %s;
                """, [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Employé non trouvé"}, status=status.HTTP_404_NOT_FOUND)

                employee = {
                    "id": row[0],
                    "matricule": row[1],
                    "full_name": row[2],
                    "job_title_id": row[3],
                    "service_id": row[4],
                    "hire_date": row[5],
                    "created_at": row[6],
                    "updated_at": row[7],
                    "profil_status": row[8]
                }
            return Response({"status": "success", "employee": employee})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """POST /employees/ → créer un nouvel employé"""
        data = request.data
        try:
            matricule = data.get("matricule")
            full_name = data.get("full_name")
            job_title_id = data.get("job_title_id")
            service_id = data.get("service_id")
            hire_date = data.get("hire_date")
            profil_status = data.get("profil_status")
            password = data.get("password")

            if not all([matricule, full_name, job_title_id, service_id]):
                return Response({"status": "error", "message": "Champs obligatoires manquants"}, status=status.HTTP_400_BAD_REQUEST)

            created_at = updated_at = datetime.now()

            hashed_password = make_password(password)  # hachage sécurisé
            # Générer un code unique
            access_code = None

            while True:
                code = generate_access_code() # encrypt this code
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM staffs WHERE access_code = %s", [code])
                    exists = cursor.fetchone()
                if not exists:
                    hashed_access_code = make_password(access_code)
                    break

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO employees (matricule, full_name, job_title_id, service_id, hire_date, created_at, updated_at,profil_status,password,access_code)
                    VALUES (%s, %s, %s, %s, %s, %s, %s,%s,%s,%s)
                    RETURNING id;
                """, [matricule, full_name, job_title_id, service_id, hire_date, created_at, updated_at,profil_status,hashed_password,hashed_access_code])
                new_id = cursor.fetchone()[0]

            return Response({"status": "success", "message": "Employé créé avec succès", "employee_id": new_id}, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None):
        """PUT /employees/{id}/ → mise à jour complète"""
        data = request.data
        try:
            matricule = data.get("matricule")
            full_name = data.get("full_name")
            job_title_id = data.get("job_title_id")
            service_id = data.get("service_id")
            hire_date = data.get("hire_date")
            profil_status = data.get("profil_status")
            access_code = data.get("access_code")
            password = data.get("password")

            if not all([matricule, full_name, job_title_id, service_id]):
                return Response({"status": "error", "message": "Champs obligatoires manquants pour PUT"}, status=status.HTTP_400_BAD_REQUEST)

            updated_at = datetime.now()

            hashed_password = make_password(password)  # hachage sécurisé

            hashed_access_code = make_password(access_code)

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE employees
                    SET matricule=%s, full_name=%s, job_title_id=%s, service_id=%s, hire_date=%s, updated_at=%s, profil_status=%s, password = %s, access_code =%s
                    WHERE id=%s
                    RETURNING id;
                """, [matricule, full_name, job_title_id, service_id, hire_date, updated_at,profil_status, hashed_password, hashed_access_code, pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Employé non trouvé"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Employé mis à jour", "employee_id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, pk=None):
        """PATCH /employees/{id}/ → mise à jour partielle"""
        data = request.data
        try:
            updated_at = datetime.now()
            set_clauses = []
            values = []

            for field in ["matricule", "full_name", "job_title_id", "service_id", "hire_date","profil_status", "password", "access_code"]:
                if field in data:
                    set_clauses.append(f"{field}=%s")
                    values.append(data[field])

            if not set_clauses:
                return Response({"status": "error", "message": "Aucun champ à mettre à jour"}, status=status.HTTP_400_BAD_REQUEST)

            set_clauses.append("updated_at=%s")
            values.append(updated_at)
            values.append(pk)

            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE employees
                    SET {', '.join(set_clauses)}
                    WHERE id=%s
                    RETURNING id;
                """, values)
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Employé non trouvé"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Employé mis à jour partiellement", "employee_id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """DELETE /employees/{id}/ → supprimer un employé"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM employees WHERE id=%s RETURNING id;", [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Employé non trouvé"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"status": "success", "message": "Employé supprimé", "employee_id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)








































