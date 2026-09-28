import argparse
import sys

from codigo.pipeline import ALL_COMMANDS, PIPELINE_STEPS, run_pipeline, run_step


def show_help(parser):
    parser.print_help()
    print("\nComandos individuais:")
    for name, (description, _) in ALL_COMMANDS.items():
        print(f"  {name:22} {description}")


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="codigo",
        description="Executa a pipeline de dados ou scripts individuais.",
    )
    parser.add_argument(
        "comando",
        nargs="?",
        choices=("pipeline", "run", "list"),
        help="pipeline: executa etapas; run: executa um script; list: lista opções",
    )

    if not arguments:
        show_help(parser)
        return 0

    command = arguments.pop(0)
    if command == "--help" or command == "-h":
        show_help(parser)
        return 0

    if command == "list":
        show_help(parser)
        return 0

    if command == "pipeline":
        pipeline_parser = argparse.ArgumentParser(
            prog="codigo pipeline",
            description="Executa todas as etapas ou somente as selecionadas.",
        )
        pipeline_parser.add_argument(
            "--only",
            nargs="+",
            choices=tuple(PIPELINE_STEPS),
            help="Executa somente estas etapas, na ordem da pipeline.",
        )
        pipeline_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra os comandos sem executá-los.",
        )
        options = pipeline_parser.parse_args(arguments)
        return run_pipeline(options.only, dry_run=options.dry_run)

    if command == "run":
        if not arguments:
            parser.error("informe um script após 'run'; use 'codigo list'")
        script = arguments.pop(0)
        if arguments and arguments[0] == "--":
            arguments.pop(0)
        try:
            return run_step(script, arguments)
        except ValueError as error:
            parser.error(str(error))

    parser.error(f"comando desconhecido: {command}")


if __name__ == "__main__":
    raise SystemExit(main())