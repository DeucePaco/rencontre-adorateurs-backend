import psycopg2
import resend
from fastapi import FastAPI, HTTPException
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

# Configuration de Resend
resend.api_key = "re_FsydLTzh_DkcsJgif8CdScDXV5qsH1vsh"  # ⚠️ REMETS TA VRAIE CLÉ ICI !

# Connexion PostgreSQL
DB_CONFIG = {
    "dbname": "adorateurs_db",
    "user": "postgres",
    "password": "admin",  # ⚠️ REMETS TON VRAI MOT DE PASSE ICI !
    "host": "localhost",
    "port": "5432"
}

class Inscription(BaseModel):
    nom: str
    email: EmailStr
    telephone: str
    ticket_id: str

@app.post("/api/envoyer-ticket")
async def inscrire_participant(donnees: Inscription):
    connection = None
    try:
        # 1. Connexion et insertion dans PostgreSQL
        connection = psycopg2.connect(**DB_CONFIG)
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
            # On utilise l'API de graphiques sécurisée de Google pour générer le QR Code en ligne
            qr_google_url = f"https://chart.googleapis.com/chart?cht=qr&chs=150x150&chl=TICKET_ID:{donnees.ticket_id}"

            html_content = f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eaeaea; border-radius: 10px;">
                <h2 style="color: #4c1d95; text-align: center;">RENCONTRE DES ADORATEURS</h2>
                <p>Bonjour <strong>{donnees.nom}</strong>,</p>
                <p>Votre inscription au programme avec <strong>Flora Akoumia</strong> a bien été confirmée !</p>
                
                <div style="background-color: #4c1d95; color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <p style="margin: 0; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">Votre Ticket d'Accès</p>
                    <h3 style="margin: 5px 0 15px 0;">FLORA AKOUMIA</h3>
                    <p style="font-size: 14px;"><strong>Date :</strong> 14 août 2026<br><strong>Lieu :</strong> Jardin Botanique</p>
                    
                    <div style="background: white; padding: 15px; display: inline-block; border-radius: 12px; margin-top: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <!-- L'image pointe vers l'adresse sécurisée de Google -->
                        <img src="{qr_google_url}" alt="Code QR" style="width: 150px; height: 150px; display: block; margin: 0 auto;" />
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