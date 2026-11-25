"""Revue d'un worktree Git avec le Copilot SDK et Context7 configuré dans Copilot CLI."""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

from copilot import CopilotClient
from copilot.session import (
    PermissionDecisionApproveOnce,
    PermissionDecisionReject,
    PermissionNoResult,
)
from copilot.session_events import AssistantMessageData, PermissionRequestRead


def trouver_racine_worktree(path: Path) -> Path:
    if not path.is_dir():
        raise ValueError(f"Le chemin n'est pas un dossier : {path}")

    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(f"Le chemin n'appartient pas à un worktree Git : {path}")
    return Path(result.stdout.strip()).resolve()


def obtenir_etat_git(worktree: Path) -> str:
    status = subprocess.run(
        ["git", "-C", str(worktree), "status", "--short", "--branch"],
        capture_output=True,
        text=True,
        check=True,
    )
    diffstat = subprocess.run(
        ["git", "-C", str(worktree), "diff", "--stat", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return (
        f"État Git (--short --branch) :\n{status.stdout.strip() or '(aucun changement)'}\n\n"
        f"Statistiques des changements (git diff --stat HEAD) :\n"
        f"{diffstat.stdout.strip() or '(aucune différence suivie)'}"
    )


def autoriser_lecture_dans(worktree: Path):
    root = os.path.normcase(os.path.realpath(worktree))

    def autoriser_lecture(request, invocation):
        if getattr(request, "managed_approval_required", False):
            return PermissionNoResult()
        if not isinstance(request, PermissionRequestRead):
            return PermissionDecisionReject()

        chemins = (request.path, request.resolved_path or request.path)
        for chemin in chemins:
            if not chemin or not os.path.isabs(chemin):
                return PermissionDecisionReject()
            candidate = os.path.normcase(os.path.realpath(chemin))
            try:
                if os.path.commonpath((root, candidate)) != root:
                    return PermissionDecisionReject()
            except ValueError:
                return PermissionDecisionReject()
        return PermissionDecisionApproveOnce()

    return autoriser_lecture


async def analyser(worktree: Path, question: str) -> str:
    etat_git = obtenir_etat_git(worktree)
    prompt = (
        f"Analyse le worktree Git situé dans {worktree}.\n\n"
        f"{etat_git}\n\n"
        f"{question}\n\n"
        "Inspecte les fichiers pertinents avec l'outil de lecture, sans rien modifier. "
        "Utilise les outils Context7 pour vérifier la documentation des bibliothèques ou "
        "API concernées lorsque cela aide l'analyse. Réponds en français, en séparant "
        "les constats vérifiés des hypothèses et en signalant les risques et tests utiles."
    )

    async with CopilotClient(mode="coding-agent") as client:
        async with await client.create_session(
            tools={"available_tools": ["builtin:view"]},
            permissions={"on_request": autoriser_lecture_dans(worktree)},
        ) as session:
            response = await session.send_and_wait(prompt, timeout=300)

    if response and isinstance(response.data, AssistantMessageData):
        return response.data.content
    raise RuntimeError("Copilot n'a pas retourné de réponse.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyse un worktree Git avec Context7 activé dans Copilot CLI."
    )
    parser.add_argument("worktree", type=Path, help="Chemin vers le worktree à analyser")
    parser.add_argument(
        "--question",
        default="Fais une revue des changements : résume-les, relève les problèmes "
        "potentiels et propose les tests pertinents.",
        help="Consigne complémentaire donnée à Copilot",
    )
    args = parser.parse_args()

    try:
        worktree = trouver_racine_worktree(args.worktree.resolve())
        print(asyncio.run(analyser(worktree, args.question)))
    except (OSError, ValueError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
