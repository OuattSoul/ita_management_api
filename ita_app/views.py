# views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db import connection
from django.db.utils import IntegrityError
from django.contrib.auth.hashers import make_password
import datetime, resend, requests, random
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.dateparse import parse_datetime

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
                    SELECT id, user_role_id, user_id, email_prof, job_title_id,
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
                    "job_title_id": row[4],
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
            fields = ["user_role_id", "user_id", "email_prof", "job_title_id",
                      "affected_at_service_id", "hire_date", "job_type_id", "profile_status"]
            values = [data.get(f) for f in fields]

            if not all(values):
                return Response({"status": "error", "message": "Tous les champs doivent être fournis pour PUT"},
                                status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE users
                    SET user_role_id=%s, user_id=%s, email_prof=%s, job_title_id=%s,
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
                if key in ["user_role_id", "user_id", "email_prof", "job_title_id",
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
                    SELECT matricule, full_name, job_title_id, service_id, hire_date,created_at,updated_at,profil_status,email_pro,job_type_id
                    FROM employees
                    ORDER BY id;
                """)
                rows = cursor.fetchall()
                employees = []
                for row in rows:
                    employees.append({
                        "matricule": row[0],
                        "full_name": row[1],
                        "job_title_id": row[2],
                        "service_id": row[3],
                        "hire_date": row[4],
                        "created_at": row[5],
                        "updated_at": row[6],
                        "profil_status": row[7],
                        "email_pro": row[8],
                        "job_type_id" : row[9]

                    })
            return Response({"status": "success", "employees": employees})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """GET /employees/{id}/ → récupérer un employé"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id,matricule, full_name, job_title_id, service_id, hire_date,
                           created_at, updated_at,profil_status,email_pro, job_type_id
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
                    "profil_status": row[8],
                    "email_pro": row[9],
                    "job_type_id" : row[10]
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
            email_pro = data.get("email_pro")
            job_type_id = data.get("job_type_id")

            if not all([matricule, full_name, job_title_id, service_id, hire_date, email_pro]):
                return Response({"status": "error", "message": "Champs obligatoires manquants"}, status=status.HTTP_400_BAD_REQUEST)

            hashed_password = make_password(password)

            # Générer un code unique pour l'accès
            while True:
                access_code = generate_access_code()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM employees WHERE access_code = %s", [access_code])
                    exists = cursor.fetchone()
                if not exists:
                    hashed_access_code = make_password(access_code)
                    break

            created_at = updated_at = datetime.datetime.now()

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO employees (matricule, full_name, job_title_id, service_id, hire_date,
                                        created_at, updated_at, profil_status, password, access_code,
                                        email_pro, job_type_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, [matricule, full_name, job_title_id, service_id, hire_date,
                    created_at, updated_at, profil_status, hashed_password, hashed_access_code,
                    email_pro, job_type_id])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Erreur lors de la création de l'employé"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                new_id = row[0]

            # Envoyer le code d'accès par email
            unplunk_send_email(full_name, email_pro, access_code)

            # ✅ Génération du token JWT avec SimpleJWT
            class DummyUser:
                """Utilisateur fictif pour SimpleJWT"""
                def __init__(self, id, full_name):
                    self.id = id
                    self.full_name = full_name

            dummy_user = DummyUser(new_id, full_name)
            refresh = RefreshToken.for_user(dummy_user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            return Response({
                "status": "success",
                "message": "Employé créé avec succès",
                "employee_id": new_id,
                "access_token": access_token,
                "refresh_token": refresh_token
            }, status=status.HTTP_201_CREATED)

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
            email_pro = data.get("email_pro")

            if not all([matricule, full_name, job_title_id, service_id]):
                return Response({"status": "error", "message": "Champs obligatoires manquants pour PUT"}, status=status.HTTP_400_BAD_REQUEST)

            updated_at = datetime.datetime.now()

            hashed_password = make_password(password)  # hachage sécurisé

            hashed_access_code = make_password(access_code)

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE employees
                    SET matricule=%s, full_name=%s, job_title_id=%s, service_id=%s, hire_date=%s, updated_at=%s, profil_status=%s, password = %s, access_code =%s, email_pro=%s
                    WHERE id=%s
                    RETURNING id;
                """, [matricule, full_name, job_title_id, service_id, hire_date, updated_at,profil_status, hashed_password, hashed_access_code,email_pro, pk])
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
            updated_at = datetime.datetime.now()
            set_clauses = []
            values = []

            for field in ["matricule", "full_name", "job_title_id", "service_id", "hire_date","profil_status","email_pro", "password", "access_code"]:
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


class RecruitmentRequestViewSet(viewsets.ViewSet):
    """
    ViewSet CRUD complet pour la table 'recruitment_requests' via SQL direct.
    """

    def list(self, request):
        """GET /recruitments/ → liste toutes les requêtes de recrutement"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT rr.id,
                           rr.priority,
                           rr.salary,
                           rr.needs,
                           rr.skills,
                           rr.created_at,
                           rr.updated_at,
                           rr.creation_date,
                           rr.recruitment_status,
                           rr.end_period,
                           s.id AS service_id,
                           s.name AS service_name,
                           s.chief AS service_chief,
                           jt.id AS job_title_id,
                           jt.title AS job_title,
                           jty.id AS job_type_id,
                           jty.type_name AS job_type
                    FROM recruitment_requests rr
                    JOIN request_service s ON rr.service_id = s.id
                    JOIN job_titles jt ON rr.job_title_id = jt.id
                    JOIN job_types jty ON rr.job_type_id = jty.id
                    ORDER BY rr.id;
                """)
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    results.append({
                        "id": r[0],
                        "priority": r[1],
                        "salary": r[2],
                        "needs": r[3],
                        "skills": r[4],
                        "created_at": r[5],
                        "updated_at": r[6],
                        "creation_date": r[7],
                        "recruitment_status": r[8],
                        "end_period": r[9],
                        "service": {
                            "id": r[10],
                            "name": r[11],
                            "chief": r[12],
                        },
                        "job_title": {
                            "id": r[13],
                            "title": r[14],
                        },
                        "job_type": {
                            "id": r[15],
                            "type_name": r[16],
                        }
                    })
            return Response({"status": "ok", "recruitments": results})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """GET /recruitments/{id}/ → récupérer une requête spécifique"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT rr.id,
                           rr.priority,
                           rr.salary,
                           rr.needs,
                           rr.skills,
                           rr.created_at,
                           rr.updated_at,
                           rr.creation_date,
                           rr.recruitment_status,
                           rr.end_period,
                           s.id AS service_id,
                           s.name AS service_name,
                           s.chief AS service_chief,
                           jt.id AS job_title_id,
                           jt.title AS job_title,
                           jty.id AS job_type_id,
                           jty.type_name AS job_type
                    FROM recruitment_requests rr
                    JOIN request_service s ON rr.service_id = s.id
                    JOIN job_titles jt ON rr.job_title_id = jt.id
                    JOIN job_types jty ON rr.job_type_id = jty.id
                    WHERE rr.id = %s;
                """, [pk])
                r = cursor.fetchone()
                if not r:
                    return Response({"status": "error", "message": "Requête non trouvée"}, status=status.HTTP_404_NOT_FOUND)
                recruitment = {
                    "id": r[0],
                    "priority": r[1],
                    "salary": r[2],
                    "needs": r[3],
                    "skills": r[4],
                    "created_at": r[5],
                    "updated_at": r[6],
                    "creation_date": r[7],
                    "recruitment_status": r[8],
                    "end_period": r[9],
                    "service": {
                        "id": r[10],
                        "name": r[11],
                        "chief": r[12],
                    },
                    "job_title": {
                        "id": r[13],
                        "title": r[14],
                    },
                    "job_type": {
                        "id": r[15],
                        "type_name": r[16],
                    }
                }
            return Response({"status": "ok", "recruitment": recruitment})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """POST /recruitments/ → créer une requête de recrutement"""
        data = request.data
        service_id = data.get("service_id")
        job_title_id = data.get("job_title_id")
        job_type_id = data.get("job_type_id")
        salary = data.get("salary")
        priority = data.get("priority")
        needs = data.get("needs")
        skills = data.get("skills")
        recruitment_status = data.get("recruitment_status")
        end_period = data.get("end_period")

        creation_date = datetime.date.today()
        created_at = datetime.datetime.now()
        updated_at = datetime.datetime.now()

        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO recruitment_requests
                    (service_id, job_title_id, job_type_id, priority, salary, needs, skills,
                     created_at, updated_at, creation_date, recruitment_status, end_period)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, [service_id, job_title_id, job_type_id, priority, salary, needs, skills,
                      created_at, updated_at, creation_date, recruitment_status, end_period])
                request_id = cursor.fetchone()[0]

            return self.retrieve(request, pk=request_id)
        except IntegrityError as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None):
        """PUT /recruitments/{id}/ → mise à jour complète"""
        data = request.data
        updated_at = datetime.datetime.now()
        fields = ["service_id", "job_title_id", "job_type_id", "priority", "salary", "needs", "skills", "recruitment_status", "end_period"]
        set_clause = []
        values = []
        for f in fields:
            if f in data:
                set_clause.append(f"{f}=%s")
                values.append(data[f])
        if not set_clause:
            return Response({"status": "error", "message": "Aucun champ fourni"}, status=status.HTTP_400_BAD_REQUEST)
        set_clause.append("updated_at=%s")
        values.append(updated_at)
        values.append(pk)

        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE recruitment_requests
                    SET {', '.join(set_clause)}
                    WHERE id=%s
                    RETURNING id;
                """, values)
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Requête non trouvée"}, status=status.HTTP_404_NOT_FOUND)
            return self.retrieve(request, pk=pk)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, pk=None):
        """PATCH /recruitments/{id}/ → mise à jour partielle"""
        return self.update(request, pk)

    def destroy(self, request, pk=None):
        """DELETE /recruitments/{id}/ → supprimer une requête"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM recruitment_requests WHERE id=%s RETURNING id;", [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Requête non trouvée"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"status": "ok", "message": "Requête supprimée", "id": pk})
        except Exception as e:
                    return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JobTitleViewSet(viewsets.ViewSet):
    """
    CRUD complet pour la table job_title via SQL direct
    """

    def list(self, request):
        """GET /job-titles/ → Liste des job titles"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, name FROM job_title ORDER BY id ASC;")
                rows = cursor.fetchall()
                data = [{"id": row[0], "name": row[1]} for row in rows]
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        """GET /job-titles/{id}/ → Récupérer un job title"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT id, name FROM job_title WHERE id = %s;", [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
                data = {"id": row[0], "name": row[1]}
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request):
        """POST /job-titles/ → Créer un job title"""
        name = request.data.get("name")
        if not name:
            return Response({"error": "Le champ 'name' est requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO job_title (name) VALUES (%s) RETURNING id;", [name])
                new_id = cursor.fetchone()[0]
            return Response({"id": new_id, "name": name}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        """PUT /job-titles/{id}/ → Modifier un job title"""
        name = request.data.get("name")
        if not name:
            return Response({"error": "Le champ 'name' est requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with connection.cursor() as cursor:
                cursor.execute("UPDATE job_title SET name = %s WHERE id = %s RETURNING id;", [name, pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"id": pk, "name": name}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        """DELETE /job-titles/{id}/ → Supprimer un job title"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM job_title WHERE id = %s RETURNING id;", [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Supprimé avec succès"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EmployeeAttendanceViewSet(viewsets.ViewSet):
    """CRUD complet pour la table presences"""

    def list(self, request):
        """GET /presences/ → récupérer tous les enregistrements"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, employee_name, employee_function, site, arrival, departure, time_worked, pointage_status
                    FROM presences
                    ORDER BY id;
                """)
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    result.append({
                        "id": row[0],
                        "employee_name": row[1],
                        "employee_function": row[2],
                        "site": row[3],
                        "arrival": row[4],
                        "departure": row[5],
                        "time_worked": str(row[6]),
                        "pointage_status": row[7],
                    })
            return Response({"status": "success", "data": result})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """GET /presences/{id}/ → récupérer un enregistrement"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, employee_name, employee_function, site, arrival, departure, time_worked, pointage_status
                    FROM presences
                    WHERE id = %s;
                """, [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Record not found"}, status=status.HTTP_404_NOT_FOUND)
                record = {
                    "id": row[0],
                    "employee_name": row[1],
                    "employee_function": row[2],
                    "site": row[3],
                    "arrival": row[4],
                    "departure": row[5],
                    "time_worked": str(row[6]),
                    "pointage_status": row[7],
                }
            return Response({"status": "success", "data": record})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """POST /presences/ → créer un enregistrement"""
        data = request.data
        try:
            employee_name = data.get("employee_name")
            employee_function = data.get("employee_function")
            site = data.get("site")
            arrival = data.get("arrival")
            departure = data.get("departure")
            time_worked = departure-arrival
            pointage_status = data.get("pointage_status")

            if not all([employee_name, employee_function, site, arrival, departure, pointage_status]):
                return Response({"status": "error", "message": "Champs obligatoires manquants"}, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO presences
                    (employee_name, employee_function, site, arrival, departure, time_worked, pointage_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, [employee_name, employee_function, site, arrival, departure, time_worked, pointage_status])
                new_id = cursor.fetchone()[0]

            return Response({"status": "success", "message": "Record created", "id": new_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None):
        """PUT /presences/{id}/ → mise à jour complète"""
        data = request.data
        try:
            employee_name = data.get("employee_name")
            employee_function = data.get("employee_function")
            site = data.get("site")
            arrival = data.get("arrival")
            departure = data.get("departure")
            time_worked = data.get("time_worked")
            pointage_status = data.get("pointage_status")

            if not all([employee_name, employee_function, site, arrival, departure, pointage_status]):
                return Response({"status": "error", "message": "Champs obligatoires manquants"}, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE presences
                    SET employee_name=%s, employee_function=%s, site=%s, arrival=%s, departure=%s, time_worked=%s, pointage_status=%s
                    WHERE id=%s
                    RETURNING id;
                """, [employee_name, employee_function, site, arrival, departure, time_worked, pointage_status, pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Record not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Record updated", "id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, pk=None):
        """PATCH /presences/{id}/ → mise à jour partielle"""
        data = request.data
        try:
            set_clauses = []
            values = []
            for field in ["employee_name", "employee_function", "site", "arrival", "departure", "time_worked", "pointage_status"]:
                if field in data:
                    set_clauses.append(f"{field}=%s")
                    values.append(data[field])

            if not set_clauses:
                return Response({"status": "error", "message": "Aucun champ à mettre à jour"}, status=status.HTTP_400_BAD_REQUEST)

            values.append(pk)
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE presences
                    SET {', '.join(set_clauses)}
                    WHERE id=%s
                    RETURNING id;
                """, values)
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Record not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Record partially updated", "id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MissionViewSet(viewsets.ViewSet):
    """CRUD complet pour la table missions"""

    def list(self, request):
        """GET /missions/ → récupérer toutes les missions"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, req_id, req_service, project_zone, people_required,
                           priority, deadline, mission_status
                    FROM missions
                    ORDER BY id;
                """)
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    result.append({
                        "id": row[0],
                        "req_id": row[1],
                        "req_service": row[2],
                        "project_zone": row[3],
                        "people_required": row[4],
                        "priority": row[5],
                        "deadline": row[6].isoformat() if row[6] else None,
                        "mission_status": row[7]
                    })
            return Response({"status": "success", "data": result})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """GET /missions/{id}/ → récupérer une mission"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, req_id, req_service, project_zone, people_required,
                           priority, deadline, mission_status
                    FROM missions
                    WHERE id = %s;
                """, [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Mission not found"}, status=status.HTTP_404_NOT_FOUND)
                mission = {
                    "id": row[0],
                    "req_id": row[1],
                    "req_service": row[2],
                    "project_zone": row[3],
                    "people_required": row[4],
                    "priority": row[5],
                    "deadline": row[6].isoformat() if row[6] else None,
                    "mission_status": row[7]
                }
            return Response({"status": "success", "data": mission})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """POST /missions/ → créer une mission"""
        data = request.data
        try:
            req_id = data.get("req_id")
            req_service = data.get("req_service")
            project_zone = data.get("project_zone")
            people_required = data.get("people_required")
            priority = data.get("priority")
            deadline = data.get("deadline")
            mission_status = data.get("mission_status")

            if not all([req_id, req_service, project_zone, people_required, priority, deadline, mission_status]):
                return Response({"status": "error", "message": "Champs obligatoires manquants"}, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO missions (req_id, req_service, project_zone, people_required, priority, deadline, mission_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, [req_id, req_service, project_zone, people_required, priority, deadline, mission_status])
                new_id = cursor.fetchone()[0]

            return Response({"status": "success", "message": "Mission créée", "id": new_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None):
        """PUT /missions/{id}/ → mise à jour complète"""
        data = request.data
        try:
            req_id = data.get("req_id")
            req_service = data.get("req_service")
            project_zone = data.get("project_zone")
            people_required = data.get("people_required")
            priority = data.get("priority")
            deadline = data.get("deadline")
            mission_status = data.get("mission_status")

            if not all([req_id, req_service, project_zone, people_required, priority, deadline, mission_status]):
                return Response({"status": "error", "message": "Champs obligatoires manquants"}, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE missions
                    SET req_id=%s, req_service=%s, project_zone=%s, people_required=%s,
                        priority=%s, deadline=%s, mission_status=%s
                    WHERE id=%s
                    RETURNING id;
                """, [req_id, req_service, project_zone, people_required, priority, deadline, mission_status, pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Mission not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Mission mise à jour", "id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, pk=None):
        """PATCH /missions/{id}/ → mise à jour partielle"""
        data = request.data
        try:
            set_clauses = []
            values = []
            for field in ["req_id", "req_service", "project_zone", "people_required", "priority", "deadline", "mission_status"]:
                if field in data:
                    set_clauses.append(f"{field}=%s")
                    values.append(data[field])

            if not set_clauses:
                return Response({"status": "error", "message": "Aucun champ à mettre à jour"}, status=status.HTTP_400_BAD_REQUEST)

            values.append(pk)
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE missions
                    SET {', '.join(set_clauses)}
                    WHERE id=%s
                    RETURNING id;
                """, values)
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Mission not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Mission partiellement mise à jour", "id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """DELETE /missions/{id}/ → supprimer une mission"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM missions WHERE id=%s RETURNING id;", [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Mission not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Mission supprimée", "id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LeaveViewSet(viewsets.ViewSet):
    """CRUD complet pour la table leaves"""

    def list(self, request):
        """GET /leaves/ → récupérer toutes les demandes de congés"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, employee_id, leave_type, start_date, end_date, duration,
                           workflow, priority, leave_status
                    FROM leaves
                    ORDER BY id;
                """)
                rows = cursor.fetchall()
                result = []
                for row in rows:
                    result.append({
                        "id": row[0],
                        "employee_id": row[1],
                        "leave_status": row[2],
                        "leave_type": row[3],
                        "start_date": row[4].isoformat() if row[4] else None,
                        "end_date": row[5].isoformat() if row[5] else None,
                        "duration": row[6],
                        "workflow": row[7],
                        "priority": row[8]
                    })
            return Response({"status": "success", "data": result})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """GET /leaves/{id}/ → récupérer une demande de congé"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, employee_id, leave_type, start_date, end_date, duration,
                           workflow, priority, leave_status
                    FROM leaves
                    WHERE id = %s;
                """, [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)
                leave = {
                    "id": row[0],
                    "leave_status": row[1],
                    "employee_function": row[2],
                    "leave_type": row[3],
                    "start_date": row[4].isoformat() if row[4] else None,
                    "end_date": row[5].isoformat() if row[5] else None,
                    "duration": row[6],
                    "workflow": row[7],
                    "priority": row[8]
                }
            return Response({"status": "success", "data": leave})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """POST /leaves/ → créer une demande de congé"""
        data = request.data
        try:
            employee_id = data.get("employee_id")
            leave_type = data.get("leave_type")
            start_date = data.get("start_date")
            end_date = data.get("end_date")
            #duration = data.get("duration")
            workflow = data.get("workflow")
            priority = data.get("priority")
            leave_status = data.get("leave_status")

            if not all([employee_id, leave_type, workflow, priority, leave_status]):
                return Response({"status": "error", "message": "Champs obligatoires manquants"}, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO leaves (employee_id, leave_type, start_date, end_date, duration,
                                        workflow, priority, leave_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """, [employee_id, leave_type, start_date, end_date, workflow, priority, leave_status])
                new_id = cursor.fetchone()[0]

            return Response({"status": "success", "message": "Leave request created", "id": new_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None):
        """PUT /leaves/{id}/ → mise à jour complète"""
        data = request.data
        try:
            employee_id = data.get("employee_id")
            leave_type = data.get("leave_type")
            start_date = data.get("start_date")
            end_date = data.get("end_date")
            #duration = data.get("duration")
            workflow = data.get("workflow")
            priority = data.get("priority")
            leave_status = data.get("leave_status")

            if not all([employee_id, leave_type, workflow, priority, leave_status]):
                return Response({"status": "error", "message": "Champs obligatoires manquants"}, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE leaves
                    SET employee_id=%s, leave_type=%s, start_date=%s, end_date=%s, duration=%s,
                        workflow=%s, priority=%s, leave_status=%s
                    WHERE id=%s
                    RETURNING id;
                """, [employee_id, leave_type, start_date, end_date, workflow, priority, leave_status, pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Leave request updated", "id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def partial_update(self, request, pk=None):
        """PATCH /leaves/{id}/ → mise à jour partielle"""
        data = request.data
        try:
            set_clauses = []
            values = []
            for field in ["employee_id","leave_type", "start_date", "end_date",
                          "workflow", "priority", "leave_status"]:
                if field in data:
                    set_clauses.append(f"{field}=%s")
                    values.append(data[field])

            if not set_clauses:
                return Response({"status": "error", "message": "Aucun champ à mettre à jour"}, status=status.HTTP_400_BAD_REQUEST)

            values.append(pk)
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE leaves
                    SET {', '.join(set_clauses)}
                    WHERE id=%s
                    RETURNING id;
                """, values)
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Leave request partially updated", "id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None):
        """DELETE /leaves/{id}/ → supprimer une demande de congé"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM leaves WHERE id=%s RETURNING id;", [pk])
                row = cursor.fetchone()
                if not row:
                    return Response({"status": "error", "message": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"status": "success", "message": "Leave request deleted", "id": pk})
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PresenceViewSet(viewsets.ViewSet):
    """CRUD pour la table presences"""

    def list(self, request):
        """GET /presences/ → lister toutes les présences"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM presences")
            columns = [col[0] for col in cursor.description]
            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return Response(data)

    def retrieve(self, request, pk=None):
        """GET /presences/{id}/ → récupérer une présence"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM presences WHERE id = %s", [pk])
            row = cursor.fetchone()
            if not row:
                return Response({"status": "error", "message": "Présence non trouvée"}, status=status.HTTP_404_NOT_FOUND)
            columns = [col[0] for col in cursor.description]
            data = dict(zip(columns, row))
        return Response(data)

    def create(self, request):
        """POST /presences/ → créer une présence"""
        data = request.data
        employee_id = data.get("employee_id")
        site = data.get("site", "")
        arrival = parse_datetime(data.get("arrival")) if data.get("arrival") else None
        departure = parse_datetime(data.get("departure")) if data.get("departure") else None
        pointage_status = data.get("pointage_status")

        # Calculer le temps travaillé en minutes
        if arrival and departure:
            time_worked = int((departure - arrival).total_seconds() / 60)
        else:
            time_worked = 0

        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO presences (employee_id, site, arrival, departure, time_worked, pointage_status)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, [employee_id, site, arrival, departure, time_worked, pointage_status])
            new_id = cursor.fetchone()[0]

        return Response({"status": "success", "id": new_id}, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """PUT /presences/{id}/ → mettre à jour une présence"""
        data = request.data
        employee_id = data.get("employee_id")
        site = data.get("site")
        arrival = parse_datetime(data.get("arrival")) if data.get("arrival") else None
        departure = parse_datetime(data.get("departure")) if data.get("departure") else None
        pointage_status = data.get("pointage_status")

        # Calculer le temps travaillé en minutes
        if arrival and departure:
            time_worked = int((departure - arrival).total_seconds() / 60)
        else:
            time_worked = 0

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE presences
                SET employee_id=%s, site=%s, arrival=%s, departure=%s, time_worked=%s, pointage_status=%s
                WHERE id=%s
            """, [employee_id, site, arrival, departure, time_worked, pointage_status, pk])

        return Response({"status": "success"}, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        """DELETE /presences/{id}/ → supprimer une présence"""
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM presences WHERE id = %s", [pk])
        return Response({"status": "success"}, status=status.HTTP_204_NO_CONTENT)























