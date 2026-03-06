#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "python-rapidjson ~= 1.2",
#   "typer ~= 0.24",
# ]
# ///

import shutil
import subprocess
from pathlib import Path
from typing import Any, Literal, cast

import rapidjson
import typer

VERSIONS_DIR = Path("versions")


CliConfigurationType = Literal["Debug", "Release"]
CliConfiguration = typer.Option("Debug", "-c", "--configuration")


json_loads = rapidjson.Decoder(
    parse_mode=rapidjson.PM_COMMENTS | rapidjson.PM_TRAILING_COMMAS
)

cli = typer.Typer(
    context_settings=dict(help_option_names=["-h", "--help"]),
    no_args_is_help=True,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)


def get_ninesols_version(game_dir: Path) -> str:
    # https://github.com/nine-sols-modding/libs-stripped/blob/main/Program.cs
    cfg_file = (
        next(game_dir.glob("*_Data")) / "StreamingAssets" / "Config" / "config.json"
    )
    with open(cfg_file, encoding="utf-8") as f:
        cfg = json_loads(f.read())
    return ".".join(cast(str, cfg["Version"]).split("-")[0].split(".")[1:])


def dotnet_build(version: str, configuration: CliConfigurationType) -> None:
    subprocess.run(
        [
            "dotnet",
            "build",
            "--configuration",
            configuration,
            f"-p:VersionsDir={VERSIONS_DIR}",
            f"-p:GameVersion={version}",
        ],
        check=True,
    )


@cli.command(no_args_is_help=True)
def add_version(
    game_dirs: list[Path] = typer.Argument(..., exists=True, file_okay=False)
) -> list[str]:
    """
    Symlink game's Managed/ directory to a sub-directory (named with game's version) under versions/
    """
    versions = []

    for game_dir in game_dirs:
        dll_dir = next(game_dir.glob("*_Data/Managed"), None)
        assert dll_dir is not None and dll_dir.is_dir()

        version = get_ninesols_version(game_dir)

        target = VERSIONS_DIR / version
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        elif target.is_symlink():
            target.unlink()

        target.absolute().symlink_to(dll_dir.absolute(), target_is_directory=True)
        versions.append(version)

    return versions


@cli.command(no_args_is_help=True)
def build_game(
    game_dirs: list[Path] = typer.Argument(..., exists=True, file_okay=False),
    configuration: CliConfigurationType = CliConfiguration,
) -> None:
    for version in add_version(game_dirs):
        dotnet_build(version, configuration)


@cli.command(no_args_is_help=True)
def build_version(
    versions: list[str] = typer.Argument(...),
    configuration: CliConfigurationType = CliConfiguration,
) -> None:
    for version in versions:
        version_dir = VERSIONS_DIR / version
        if not version_dir.is_dir():
            print(f'No such directory: "{VERSIONS_DIR / version}"')
            exit(1)

        dotnet_build(version, configuration)


@cli.command(no_args_is_help=True)
def build_all(configuration: CliConfigurationType = CliConfiguration) -> None:
    for version in (it for it in VERSIONS_DIR.iterdir() if it.is_dir()):
        dotnet_build(version.name, configuration)


def main() -> None:
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

    cli()


if __name__ == "__main__":
    main()
