# -*- coding: utf-8 -*-
from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.db import connection, OperationalError,IntegrityError
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from rest_framework.permissions import IsAuthenticated
import random
import os
import resend, requests
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone

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

@api_view(["GET"])
def db_connectivity(request):
    """
    Endpoint pour tester la connexion à la base de données.
    Retourne 'ok' si la connexion fonctionne, sinon 'error'.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
        return Response({"status": "ok", "message": "Connexion DB réussie ✅"})
    except OperationalError as e:
        return Response({"status": "error", "message": str(e)}, status=500)

@api_view(["GET"])
def get_users_query(request):
    """
    Endpoint qui exécute un SELECT sur la table 'api_project' et retourne les résultats.
    La requête SQL est définie côté serveur.
    """
    # Requête SQL prédéfinie
    sql = "SELECT * FROM ita_staff_users;"
    try:
        with connection.cursor() as cursor:
            
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Transformer le résultat en liste de dictionnaires
        results = [dict(zip(columns, row)) for row in rows]

        return Response({"status": "ok", "results": results})

    except OperationalError as e:
        return Response({"status": "error", "message": str(e)}, status=500)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=400)


# ita staff
@api_view(["POST"])
def register_staff(request):
    """
    Endpoint pour enregistrer un utilisateur dans PostgreSQL via INSERT
    et renvoyer JWT.
    JSON attendu :
    {
        "username": "utilisateur_pg",
        "email": "user_pg@example.com",
        "password": "MotDePasse123"
    }
    """
    data = request.data
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    user_email = data.get("user_email")
    role = data.get("role")
    password = data.get("password")
    created_at = timezone.now()
    updated_at = timezone.now()
    last_login = timezone.now()

    if not all([first_name, last_name, role, password, user_email]):
        return Response({"status": "error", "message": "Tous les champs sont requis"},
                        status=status.HTTP_400_BAD_REQUEST)  

    try:
        hashed_password = make_password(password)  # hachage sécurisé
        # Générer un code unique
        access_code = None

        while True:
            code = generate_access_code() # encrypt this code
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM ita_staff_users WHERE access_code = %s", [code])
                exists = cursor.fetchone()
            if not exists:
                access_code = code
                break


        with connection.cursor() as cursor:
            # INSERT dans users_table
            cursor.execute("""
                INSERT INTO ita_staff_users (first_name,last_name,user_email,role,access_code,password,created_at,updated_at,last_login)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, [first_name, last_name, user_email, role,access_code, hashed_password, created_at, updated_at, last_login])

            user_id = cursor.fetchone()[0]
            #resend_send_email(first_name,user_email,access_code)
            unplunk_send_email(first_name,user_email,access_code)

            payload_user = type('UserDummy', (object,), {"id": user_id, "first_name": first_name})
            refresh = RefreshToken.for_user(payload_user)
            access_token = str(refresh.access_token)

            return Response({
                "status": "ok",
                "message": f"Utilisateur '{first_name}' créé dans PostgreSQL",
                "access_token": access_token,
                #"refresh_token": refresh_token
            })
        
    except IntegrityError as e:
        return Response({"status": "error", "message": "username ou email déjà utilisé"},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def login_staff(request):
    """
    Login utilisateur avec fname + password
    (table Postgres 'users' : id, fname, lname, role, password)
    """
    access_code = request.data.get("access_code")
    #password = request.data.get("password")

    if not access_code:
        return Response({"error": "Code d'accès requis"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, first_name, last_name, role FROM ita_staff_users WHERE access_code = %s", [access_code])
            row = cursor.fetchone()

        if row is None:
            return Response({"error": "Utilisateur non trouvé"}, status=status.HTTP_404_NOT_FOUND)

        user_id, first_name, last_name, role = row

        # Vérification du mot de passe
        #if not check_password(password, db_password):
        #    return Response({"error": "Mot de passe incorrect"}, status=status.HTTP_401_UNAUTHORIZED)

       

        return Response({
            #"refresh": str(refresh),
            #"access": str(refresh.access_token),
            "user": {
                "id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def get_staff(request):
    # Requête SQL prédéfinie
    sql = "SELECT id, first_name, last_name, role, user_email FROM ita_staff_users;"
    try:
        with connection.cursor() as cursor:
            
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Transformer le résultat en liste de dictionnaires
        results = [dict(zip(columns, row)) for row in rows]

        return Response({"status": "ok", "results": results})

    except OperationalError as e:
        return Response({"status": "error", "message": str(e)}, status=500)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=400)

# assign mission
@api_view(["POST"])
def assign_mission(request):
    data = request.data
    project = data.get("project")
    mission_type = data.get("mission_type")
    people_count = data.get("people_count")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    urgency_level = data.get("urgency_level")
    special_instructions = data.get("special_instructions")
    created_at = timezone.now()

    if not all([project, mission_type, people_count, start_date, end_date, urgency_level, special_instructions]):
        return Response({"status": "error", "message": "Tous les champs sont requis"},
                        status=status.HTTP_400_BAD_REQUEST)  

    try:
        with connection.cursor() as cursor:
            # INSERT dans users_table
            cursor.execute("""
                INSERT INTO assign_missions (project,mission_type,people_count,start_date,end_date,urgency_level,special_instructions,created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s,%s)
                RETURNING id;
            """, [project, mission_type, people_count, start_date,end_date, urgency_level,special_instructions, created_at])

            project_id = cursor.fetchone()[0]
           

            return Response({
                "status": "ok",
                "message": f"Projet '{project}' assigné dans avec succès"
            })
    
    except IntegrityError as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def get_missions(request):
    # Requête SQL prédéfinie
    sql = "SELECT * FROM assign_missions;"
    try:
        with connection.cursor() as cursor:
            
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Transformer le résultat en liste de dictionnaires
        results = [dict(zip(columns, row)) for row in rows]

        return Response({"status": "ok", "results": results})

    except OperationalError as e:
        return Response({"status": "error", "message": str(e)}, status=500)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=400)

# leave request
@api_view(["POST"])
def set_leaves(request):
    data = request.data
    employee_id = data.get("employee_id")
    employee_function = data.get("employee_function")
    leave_type = data.get("leave_type")
    reason = data.get("reason")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    duration = data.get("duration")
    workflow = data.get("workflow")
    status = data.get("status")
    priority = data.get("priority")
    created_at = timezone.now()

    if not all([employee_id, leave_type,employee_function, reason, start_date, end_date, duration, workflow,status, priority]):
        return Response({"status": "error", "message": "Tous les champs sont requis"},
                        status=status.HTTP_400_BAD_REQUEST)  

    try:
        with connection.cursor() as cursor:
            # INSERT dans users_table
            cursor.execute("""
                INSERT INTO leaves (employee_id,leave_type,employee_function,reason,start_date,end_date,duration,workflow,status,priority,created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s,%s)
                RETURNING id;
            """, [employee_id,leave_type,employee_function,reason,start_date,end_date,duration,workflow,status,priority,created_at])

            leave_id = cursor.fetchone()[0]
           

            return Response({
                "status": "ok",
                "message": f"Congé '{leave_type}' enregistré dans avec succès"
            })
    
    except IntegrityError as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_leaves(request):
    # Requête SQL prédéfinie
    sql = "SELECT * FROM leaves;"
    try:
        with connection.cursor() as cursor:
            
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Transformer le résultat en liste de dictionnaires
        results = [dict(zip(columns, row)) for row in rows]

        return Response({"status": "ok", "results": results})

    except OperationalError as e:
        return Response({"status": "error", "message": str(e)}, status=500)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=400)


# recruitment
@api_view(["POST"])
def request_recruitment(request):
    data = request.data
    job_type = data.get("job_type")
    req_service = data.get("req_service")
    job_title = data.get("job_title")
    priority = data.get("priority")
    status = data.get("status")
    salary = data.get("salary")
    needs = data.get("needs")
    skills = data.get("skills")
    created_at = timezone.now()

    if not all([job_type,job_title, salary, req_service, priority, needs, skills, priority]):
        return Response({"status": "error", "message": "Tous les champs sont requis"},
                        status=status.HTTP_400_BAD_REQUEST)  

    try:
        with connection.cursor() as cursor:
            # INSERT dans users_table
            cursor.execute("""
                INSERT INTO recruitments (job_title,req_service,job_type,status_field,salary,skills,created_at,priority)
                VALUES (%s, %s, %s, %s, %s, %s, %s,%s)
                RETURNING id;
            """, [job_title, req_service, job_type, status, salary, skills, created_at, priority])

            leave_id = cursor.fetchone()[0]
           

            return Response({
                "status": "ok",
                "message": f"Requête de recrutement {job_title} envoyée dans avec succès"
            })
    
    except IntegrityError as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_recruitments(request):
    # Requête SQL prédéfinie
    sql = "SELECT * FROM recruitments;"
    try:
        with connection.cursor() as cursor:
            
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Transformer le résultat en liste de dictionnaires
        results = [dict(zip(columns, row)) for row in rows]

        return Response({"status": "ok", "results": results})

    except OperationalError as e:
        return Response({"status": "error", "message": str(e)}, status=500)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=400)


# pointage
@api_view(["POST"])
def presence_pointage(request):
    data = request.data
    employee_id = data.get("employee_id")
    employee_function = data.get("employee_function")
    site = data.get("site")
    arrival = data.get("arrival")
    departure = data.get("departure")
    time_worked = data.get("time_worked")

    if not all([employee_id,employee_function, site, arrival, departure, time_worked]):
        return Response({"status": "error", "message": "Tous les champs sont requis"},
                        status=status.HTTP_400_BAD_REQUEST)  

    try:
        with connection.cursor() as cursor:
            # INSERT dans users_table
            cursor.execute("""
                INSERT INTO recruitments (employee_id,employee_function,site,arrival,departure,time_worked)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, [employee_id, employee_function, site, arrival, departure, time_worked])

            leave_id = cursor.fetchone()[0]
           

            return Response({
                "status": "ok",
                "message": f"Pointage enregistré avec succès"
            })
    
    except IntegrityError as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"status": "error", "message": str(e)},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# get pointage
@api_view(["GET"])
def get_pointage(request):
    # Requête SQL prédéfinie
    sql = "SELECT * FROM presences;"
    try:
        with connection.cursor() as cursor:
            
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Transformer le résultat en liste de dictionnaires
        results = [dict(zip(columns, row)) for row in rows]

        return Response({"status": "ok", "results": results})

    except OperationalError as e:
        return Response({"status": "error", "message": str(e)}, status=500)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=400)
    
# employee management

@api_view(["POST"])
#@parser_classes([MultiPartParser, FormParser])
def create_employee(request):
    """
    Crée un employé avec tous les champs (infos personnelles, professionnelles et documents).
    """
    data = request.data

    # Champs personnels
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    nationality = data.get("nationality")
    birth_date = data.get("birth_date")
    birth_place = data.get("birth_place")
    full_address = data.get("full_address")
    phone = data.get("phone")
    email = data.get("email")
    emergency_contact_name = data.get("emergency_contact_name", "")
    emergency_contact_phone = data.get("emergency_contact_phone", "")

    # Champs professionnels
    job_type = data.get("job_type")  # CDI, CDD, Intérim
    diploma = data.get("diploma", "")
    additional_training = data.get("additional_training", "")
    professional_certificate = data.get("professional_certificate", "")
    spoken_languages = data.get("spoken_languages", "")
    language_level = data.get("language_level")  # B2, A1, A2

    # 
    current_position = data.get("current_position", "")
    company = data.get("company", "")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    moral_reference = data.get("moral_reference", "")
    employment_type_field = data.get("employment_type")  # CDI, CDD, Intérim
    hire_date = data.get("hire_date")
    rattached_service = data.get("rattached_service", "")
    base_salary = data.get("base_salary")
    bonuses = data.get("bonuses", "")
    probation_period = data.get("probation_period")
    occupied_role = data.get("occupied_role")

    # Gestion fichiers
    certificate_file = None
    portfolio_file = None

    if "certificate_file" in request.FILES:
        file_obj = request.FILES["certificate_file"]
        file_path = f"uploads/certificates/{file_obj.name}"
        with open(file_path, "wb+") as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        certificate_file = file_path

    if "portfolio_file" in request.FILES:
        file_obj = request.FILES["portfolio_file"]
        file_path = f"uploads/portfolio/{file_obj.name}"
        with open(file_path, "wb+") as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        portfolio_file = file_path

    # Vérification des champs obligatoires
    required_fields = [first_name, last_name, nationality, birth_date, birth_place, full_address, phone, email, job_type, language_level]
    if not all(required_fields):
        return Response({"error": "Tous les champs obligatoires doivent être remplis."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO employees
                (first_name, last_name, nationality, birth_date, birth_place, full_address, phone, email,
                 emergency_contact_name, emergency_contact_phone,
                 job_type, diploma,certificate_file, additional_training, professional_certificate,
                 spoken_languages, language_level,
                 current_position, company, start_date, end_date, moral_reference, portfolio_file,
                 employment_type_field, hire_date, rattached_service, occupied_role, base_salary, bonuses, probation_period)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                [first_name, last_name, nationality, birth_date, birth_place, 
                 full_address, phone, email, emergency_contact_name, emergency_contact_phone,
                 job_type, diploma, certificate_file, additional_training, professional_certificate,
                 spoken_languages, language_level, current_position, company, start_date, 
                 end_date, moral_reference, portfolio_file, employment_type_field, hire_date, 
                 occupied_role,rattached_service, base_salary, bonuses, probation_period
                ]
            )
            new_id = cursor.fetchone()[0]

        return Response({
            "message": "Employé ajouté avec succès",
            "employee_id": new_id,
            "data": data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_employees(request):
    # Requête SQL prédéfinie
    sql = "SELECT * FROM employees;"
    try:
        with connection.cursor() as cursor:
            
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Transformer le résultat en liste de dictionnaires
        results = [dict(zip(columns, row)) for row in rows]

        return Response({"status": "ok", "results": results})

    except OperationalError as e:
        return Response({"status": "error", "message": str(e)}, status=500)
    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=400)



















































