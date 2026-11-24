# demande.py — premier essai du Copilot SDK (microsoft-copilot-sdk 2.0.1)
import asyncio
import os

from copilot import CopilotClient
from copilot.rpc import PermissionDecisionApproveOnce, PermissionDecisionReject
from copilot.session import PermissionNoResult
from copilot.session_events import AssistantMessageData, PermissionRequestRead

# Fichier joint à la question : un petit module de chartier (65 lignes)
FICHIER = r"C:\chartier-ci\api_py\tuiles.py"


def autoriser_lecture(request, invocation):
    if getattr(request, "managed_approval_required", False):
        return PermissionNoResult()
    if isinstance(request, PermissionRequestRead):
        chemins = (request.path, request.resolved_path or request.path)
        fichier = os.path.normcase(os.path.realpath(FICHIER))
        if all(
            os.path.isabs(chemin) and os.path.normcase(os.path.realpath(chemin)) == fichier
            for chemin in chemins
        ):
            return PermissionDecisionApproveOnce()
    return PermissionDecisionReject()


async def main():
    async with CopilotClient(mode="coding-agent") as client:
        async with await client.create_session(
            # Un seul outil : la lecture de fichiers. Copilot ne peut ni écrire,
            # ni lancer de commande.
            tools={"available_tools": ["builtin:view"]},
            permissions={"on_request": autoriser_lecture},
        ) as session:
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
