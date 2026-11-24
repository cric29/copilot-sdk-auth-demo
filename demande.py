# demande.py — premier essai du Copilot SDK (microsoft-copilot-sdk 2.0.1)
import asyncio

from copilot import CopilotClient
from copilot.session_events import AssistantMessageData

# Fichier joint à la question : un petit module de chartier (65 lignes)
FICHIER = r"C:\chartier-ci\api_py\tuiles.py"


async def main():
    async with CopilotClient(mode="coding-agent") as client:
        async with await client.create_session(
            # Aucun outil : Copilot ne peut ni lire d'autres fichiers, ni écrire,
            # ni lancer de commande. Il ne voit que le fichier joint.
            # Un seul outil : la lecture de fichiers. Copilot ne peut ni écrire,
            # ni lancer de commande.
            tools={"available_tools": ["builtin:view"]},        ) as session:
            reponse = await session.send_and_wait(
                "Explique en français, en cinq lignes, ce que fait ce module "
                "et pourquoi il a deux moteurs.",
                attachments=[{"type": "file", "path": FICHIER}],
                timeout=180,  # 3 min : le premier lancement télécharge le moteur
            )
            if reponse and isinstance(reponse.data, AssistantMessageData):
                print(reponse.data.content)
            else:
                print("Pas de réponse reçue.")


asyncio.run(main())
