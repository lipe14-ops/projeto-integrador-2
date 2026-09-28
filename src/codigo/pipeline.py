import subprocess
import sys
from pathlib import Path
from shlex import join


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_STEPS = {
    "municipios": (
        "Gera os arquivos de municípios",
        (sys.executable, "-m", "scripts.get_municipios"),
    ),
    "migrar-banco": (
        "Aplica as migrações do banco",
        (sys.executable, "-m", "alembic", "upgrade", "head"),
    ),
    "enviar-municipios": (
        "Carrega municípios no PostgreSQL/PostGIS",
        (sys.executable, "-m", "scripts.upload_municipios"),
    ),
    "baixar-clima": (
        "Baixa os arquivos ERA5-Land",
        (sys.executable, "-m", "scripts.get_climate"),
    ),
    "carregar-clima": (
        "Carrega dados ERA5-Land no banco",
        (sys.executable, "-m", "scripts.upload_climate"),
    ),
}

UTILITY_COMMANDS = {
    "consultar-municipios": (
        "Consulta os municípios gerados",
        (sys.executable, "-m", "scripts.read_municipios"),
    ),
    "consultar-clima": (
        "Consulta os arquivos climáticos",
        (sys.executable, "-m", "scripts.read_climate"),
    ),
}

ALL_COMMANDS = PIPELINE_STEPS | UTILITY_COMMANDS


def run_command(name, command, arguments=(), dry_run=False):
    full_command = [*command, *arguments]
    print(f"\n==> {name}", flush=True)
    if dry_run:
        print(join(full_command))
        return 0

    result = subprocess.run(full_command, cwd=PROJECT_ROOT, check=False)
    return result.returncode


def run_step(name, arguments=(), dry_run=False):
    if name not in ALL_COMMANDS:
        available = ", ".join(ALL_COMMANDS)
        raise ValueError(f"Etapa desconhecida: {name}. Opções: {available}")

    _, command = ALL_COMMANDS[name]
    return run_command(name, command, arguments, dry_run=dry_run)


def run_pipeline(steps=None, dry_run=False):
    requested_steps = list(steps) if steps is not None else list(PIPELINE_STEPS)
    unknown_steps = [step for step in requested_steps if step not in PIPELINE_STEPS]
    if unknown_steps:
        available = ", ".join(PIPELINE_STEPS)
        raise ValueError(
            f"Etapas inválidas: {', '.join(unknown_steps)}. Opções: {available}"
        )
    selected_steps = [step for step in PIPELINE_STEPS if step in requested_steps]

    for index, name in enumerate(selected_steps, start=1):
        description, command = PIPELINE_STEPS[name]
        print(f"\n[{index}/{len(selected_steps)}] {description}", flush=True)
        return_code = run_command(name, command, dry_run=dry_run)
        if return_code:
            print(f"Etapa '{name}' terminou com código {return_code}.")
            return return_code

    print("\nPipeline concluída.")
    return 0