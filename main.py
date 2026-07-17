import os
import psycopg2
import resend
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

app = FastAPI(title="API Inscription Adorateurs")

# CORS indispensables
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration de Resend via Variables d'environnement (plus sécurisé en production)
resend.api_key = os.getenv("RESEND_API_KEY", "re_FsydLTzh_DkcsJgif8CdScDXV5qsH1vsh")

# Connexion PostgreSQL dynamique (Prend l'URL en ligne, ou se rabat sur ton localhost en local)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:admin@localhost:5432/adorateurs_db")

class Inscription(BaseModel):
    nom: str
    email: EmailStr
    telephone: str
    ticket_id: str

# Fonction utilitaire pour obtenir une connexion à la base de données
def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Erreur de connexion à la base de données : {e}")
        raise HTTPException(status_code=500, detail="Impossible de se connecter à la base de données.")

@app.post("/api/envoyer-ticket")
async def inscrire_participant(donnees: Inscription):
    connection = None
    try:
        # 1. Connexion et insertion dans PostgreSQL
        connection = get_db_connection()
        cursor = connection.cursor()
        insert_query = """
        INSERT INTO participants (nom, email, telephone, ticket_id) 
        VALUES (%s, %s, %s, %s);
        """
        cursor.execute(insert_query, (donnees.nom, donnees.email, donnees.telephone, donnees.ticket_id))
        connection.commit()
        cursor.close()
        print(f"[{donnees.ticket_id}] Enregistré dans PostgreSQL !")
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Erreur DB : {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la sauvegarde en BD.")
    finally:
        if connection:
            connection.close()

    # 2. Envoi d'email via le générateur sécurisé de Google
    if "re_" in resend.api_key:
        try:
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=TICKET_ID:{donnees.ticket_id}"

            html_content = f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 10px;">
                <h2 style="color: #4c1d95; text-align: center;">RENCONTRE DES ADORATEURS</h2>
                <p>Bonjour <strong>{donnees.nom}</strong>,</p>
                <p>Votre inscription au programme  <strong>Rencontre des adorateurs</strong> a bien été confirmée !</p>
                
                <div style="background-color: #4c1d95; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <p style="margin: 0; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">Votre Ticket d'Accès</p>
                    <h3 style="margin: 5px 0 15px 0;">{donnees.nom}</h3>
                    <p style="font-size: 14px;"><strong>Date :</strong> 14 août 2026<br><strong>Lieu :</strong> Jardin Botanique</p>
                    
                    <div style="background: white; padding: 15px; display: inline-block; border-radius: 12px; margin-top: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <img src="{qr_url}" alt="Code QR" style="width: 150px; height: 150px; display: block; margin: 0 auto;" />
                        <p style="color: #333; margin: 8px 0 0 0; font-weight: bold; font-size: 12px; letter-spacing: 1px;">#{donnees.ticket_id}</p>
                    </div>
                </div>
            </div>
            """
            resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": donnees.email,
                "subject": "Confirmation Inscription - Adorateurs 🎟️",
                "html": html_content
            })
            print("E-mail envoyé avec le QR Code de Google !")
        except Exception as e:
            print(f"Erreur email : {e}")

    return {"statut": "success"}

# === NOUVELLE ROUTE POUR TON INTERFACE ADMIN ===
@app.get("/api/admin/participants")
async def obtenir_participants():
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT id, nom, email, telephone, ticket_id, cree_at FROM participants ORDER BY cree_at DESC;")
        lignes = cursor.fetchall()
        cursor.close()
        
        # Structurer les données proprement pour ton tableau d'administration
        participants = []
        for l in lignes:
            participants.append({
                "id": l[0],
                "nom": l[1],
                "email": l[2],
                "telephone": l[3],
                "ticket_id": l[4],
                "cree_at": str(l[5])
            })
        return participants
    except Exception as e:
        print(f"Erreur lors de la récupération : {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des participants.")
    finally:
        if connection:
            connection.close()
    class ValidationTicket(BaseModel):
    ticket_id: str

@app.post("/api/admin/verifier-ticket")
async def verifier_ticket(donnees: ValidationTicket):
    connection = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # 1. On cherche le participant avec ce ticket
        cursor.execute("SELECT nom, email FROM participants WHERE ticket_id = %s;", (donnees.ticket_id,))
        resultat = cursor.fetchone()
        
        if resultat is None:
            raise HTTPException(status_code=404, detail="Ticket invalide ou introuvable.")
            
        nom_participant = resultat[0]
        cursor.close()
        
        return {
            "statut": "valide",
            "message": f"Ticket valide pour {nom_participant} !",
            "nom": nom_participant
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Erreur vérification : {e}")
        raise HTTPException(status_code=500, detail="Erreur lors de la vérification du ticket.")
    finally:
        if connection:
            connection.close()