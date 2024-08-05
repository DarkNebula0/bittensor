# Standard Library
import argparse
import os
import yaml

# 3rd Party
from rich.prompt import Prompt
from rich.table import Table

# Bittensor
import bittensor
from ..utils.logger import log_error_with_exception, log_error, log_info, log_warning
from ..utils.data import unflatten_dict, flatten_dict

# Local
from . import defaults


def list_profiles(path):
    try:
        os.makedirs(path, exist_ok=True)
        files = os.listdir(path)
        profiles = [profileFile for profileFile in files if profileFile.endswith(".yml")]
    except Exception as e:
        log_error_with_exception("Failed to list profiles", e)
        return []

    if not profiles:
        log_error(f"No profiles found in {path}")
        return []

    return profiles


def get_profile_file_path(path, profile_name):
    """Return the profile file path with the correct extension."""
    profiles = list_profiles(path)
    profile_base_name = profile_name.replace('.yml', '')

    for profile in profiles:
        if profile.startswith(profile_base_name):
            return os.path.join(path, profile)

    log_error_with_exception(f"Profile {profile_name} not found in {path}", None)
    return None


def get_profile_path_from_config(cli):
    """Extract profile path from config"""
    config = cli.config
    path = os.path.expanduser(config.profile.path)
    return get_profile_file_path(path, config.profile.name)


def open_profile(cli):
    """Open a profile and return its configuration and contents."""
    profile_path = get_profile_path_from_config(cli)

    if profile_path is None:
        return None, None

    try:
        with open(profile_path, "r") as f:
            config_content = f.read()
        contents = yaml.safe_load(config_content)
        return profile_path, contents
    except Exception as e:
        log_error_with_exception("Failed to read profile", e)
        return None, None


class ProfileCreateCommand:
    """
    Executes the ``create`` command.

    This class provides functionality to create a profile by using the provided command-line arguments.
    The entered attributes are then written to a profile file.

    """

    @staticmethod
    def run(cli):
        ProfileCreateCommand._run(cli)

    @staticmethod
    def _run(cli: "bittensor.cli"):
        parsed_params = {}
        values = cli.config.get("values")

        if not values:
            log_error(
                "No key-value pairs provided. Please provide --values key=value key=value ... pairs to set in the "
                "profile file.")
            return

        for arg in values:
            if '=' in arg:
                key, value = arg.split('=', 1)
                parsed_params[key] = value

        if not parsed_params.__sizeof__() > 0:
            log_error("Invalid values provided. Please provide --values key=value key=value ... pairs to set in the "
                      "profile file.")
            return

        ProfileCreateCommand._write_profile(cli.config, unflatten_dict(parsed_params))

    @staticmethod
    def _write_profile(config: "bittensor.config", content):
        path = os.path.expanduser(config.profile.path)
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            log_error_with_exception("Failed to write profile", e)
            return

        profile_file = f"{path}{config.profile.name}.yml"
        if os.path.exists(profile_file) and not config.no_prompt:
            overwrite = None
            while overwrite not in ["y", "n"]:
                overwrite = Prompt.ask(f"Profile {config.profile.name} already exists. Overwrite?")
                if overwrite:
                    overwrite = overwrite.lower()
            if overwrite == "n":
                log_error("Failed to write profile: User denied.")
                return

        try:
            with open(profile_file, "w+") as file:
                yaml.safe_dump(content, file)
        except Exception as e:
            log_error_with_exception("Failed to write profile", e)
            return

        log_info(f"Profile {config.profile.name} written to {path}")

    @staticmethod
    def check_config(config: "bittensor.config"):
        profile = config.get("profile", {})
        name = profile.get("name")
        path = profile.get("path")
        # TODO: Check; This should never been possible because of the defaults which are set in the argument parser
        # Is there any case where this function is useful?
        return name is not None and path is not None

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        profile_parser = parser.add_parser("create", help="""Create profile""")
        profile_parser.set_defaults(func=ProfileCreateCommand.run)
        profile_parser.add_argument(
            "--profile.name",
            type=str,
            default=defaults.profile.name,
            help="The name of the profile",
        )
        profile_parser.add_argument(
            "--profile.path",
            type=str,
            default=defaults.profile.path,
            help="The path to the profile directory",
        )
        profile_parser.add_argument("--values", nargs=argparse.REMAINDER,
                                    help="The key=value pairs to set in the profile file")


class ProfileListCommand:
    @staticmethod
    def run(cli):
        ProfileListCommand._run(cli)

    @staticmethod
    def _run(cli: "bittensor.cli"):
        config = cli.config
        active_profile = config.profile.active
        path = os.path.expanduser(config.profile.path)
        profiles = list_profiles(path)
        if not profiles:
            # Error message already printed in list_profiles
            return

        profile_content = []
        for profile in profiles:
            profile_name = profile.replace('.yml', '')
            if profile_name == active_profile:
                profile_content.append(["*", profile_name])
            else:
                profile_content.append(["", profile_name])

        table = Table(show_footer=True, width=cli.config.get("width", None), pad_edge=True, box=None, show_edge=True)
        table.title = "[white]Profiles"
        table.add_column("Active", style="red", justify="center", min_width=1)
        table.add_column("Name", style="white", justify="left", min_width=20)

        for profile in profile_content:
            table.add_row(*profile)

        bittensor.__console__.print(table)

    @staticmethod
    def check_config(config: "bittensor.config"):
        profile = config.get("profile", {})
        path = profile.get("path")
        # TODO: Check; This should never been possible because of the defaults which are set in the argument parser
        # Is there any case where this function is useful?
        return path is not None

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        profile_parser = parser.add_parser("list", help="""List profiles""")
        profile_parser.set_defaults(func=ProfileListCommand.run)
        profile_parser.add_argument("--profile.path", type=str, default=defaults.profile.path,
                                    help="The path to the profile directory")


class ProfileShowCommand:
    @staticmethod
    def run(cli):
        ProfileShowCommand._run(cli)

    @staticmethod
    def _run(cli: "bittensor.cli"):
        config = cli.config
        _profile_path, contents = open_profile(cli)

        if contents is None:
            # Error message already printed in get_profile_file_path
            return

        table = Table(show_footer=True, width=cli.config.get("width", None), pad_edge=True, box=None, show_edge=True)
        table.title = f"[white]Profile [bold white]{config.profile.name}"
        table.add_column("[overline white]PARAMETERS", style="bold white", justify="left", min_width=15)
        table.add_column("[overline white]VALUES", style="green", justify="left", min_width=20)
        flat_contents = flatten_dict(contents)

        for key in flat_contents:
            table.add_row(f"  [bold white]{key}", f"[green]{flat_contents[key]}")

        bittensor.__console__.print(table)

    @staticmethod
    def check_config(config: "bittensor.config"):
        profile = config.get("profile", {})
        name = profile.get("name")
        path = profile.get("path")
        # TODO: Check; This should never been possible because of the defaults which are set in the argument parser
        # Is there any case where this function is useful?
        return name is not None and path is not None

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        profile_parser = parser.add_parser("show", help="""Show profile""")
        profile_parser.set_defaults(func=ProfileShowCommand.run)
        profile_parser.add_argument("--profile.name", type=str, help="The name of the profile")
        profile_parser.add_argument("--profile.path", type=str, default=defaults.profile.path,
                                    help="The path to the profile directory")


class ProfileDeleteCommand:
    @staticmethod
    def run(cli):
        ProfileDeleteCommand._run(cli)

    @staticmethod
    def _run(cli: "bittensor.cli"):
        config = cli.config
        profile_path = get_profile_path_from_config(cli)

        if profile_path is None:
            # Error message already printed in get_profile_file_path
            return

        try:
            os.remove(profile_path)
            log_info(f"Profile {config.profile.name} deleted from {os.path.expanduser(config.profile.path)}")
        except Exception as e:
            log_error_with_exception("Failed to delete profile", e)

    @staticmethod
    def check_config(config: "bittensor.config"):
        profile = config.get("profile", {})
        name = profile.get("name")
        path = profile.get("path")
        # TODO: Check; This should never been possible because of the defaults which are set in the argument parser
        # Is there any case where this function is useful?
        return name is not None and path is not None

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        profile_parser = parser.add_parser("delete", help="""Delete profile""")
        profile_parser.set_defaults(func=ProfileDeleteCommand.run)
        profile_parser.add_argument("--profile.name", type=str, help="The name of the profile to delete")
        profile_parser.add_argument("--profile.path", type=str, default=defaults.profile.path,
                                    help="The path to the profile directory")


class ProfileSetValueCommand:
    @staticmethod
    def run(cli):
        ProfileSetValueCommand._run(cli)

    @staticmethod
    def _run(cli: "bittensor.cli"):
        config = cli.config
        profile_path, contents = open_profile(cli)
        values = cli.config.get("values")

        if not values:
            log_error(
                "No key-value pairs provided. Please provide --values key=value key=value ... pairs to set in the "
                "profile file.")
            return

        if profile_path is None:
            # Error message already printed in open_profile
            return

        flatten_contents = flatten_dict(contents)

        # Parse the new value from the arguments
        for arg in values:
            if "=" in arg:
                key, value = arg.split("=")
                if flatten_contents.__contains__(key):
                    log_info(f"Variable {key} was updated to {value} in profile {config.profile.name}")
                else:
                    log_info(f"Variable {key} was created with value {value} in profile {config.profile.name}")

                flatten_contents[key] = value

        try:
            with open(profile_path, "w") as f:
                yaml.safe_dump(unflatten_dict(flatten_contents), f)
        except Exception as e:
            log_error_with_exception("Failed to write profile", e)

    @staticmethod
    def check_config(config: "bittensor.config"):
        profile = config.get("profile", {})
        name = profile.get("name")
        path = profile.get("path")
        # TODO: Check; This should never been possible because of the defaults which are set in the argument parser
        # Is there any case where this function is useful?
        return name is not None and path is not None

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        profile_parser = parser.add_parser("set_value", help="""Set or update profile values""")
        profile_parser.set_defaults(func=ProfileSetValueCommand.run)
        profile_parser.add_argument("--profile.name", type=str, help="The name of the profile to update")
        profile_parser.add_argument("--profile.path", type=str, default=defaults.profile.path,
                                    help="The path to the profile directory")
        profile_parser.add_argument("--values", nargs=argparse.REMAINDER, help="The key=value pairs to set or update")


class ProfileDeleteValueCommand:
    @staticmethod
    def run(cli):
        ProfileDeleteValueCommand._run(cli)

    @staticmethod
    def _run(cli: "bittensor.cli"):
        config = cli.config
        profile_path, contents = open_profile(cli)
        values = cli.config.get("values")

        if not values:
            log_error(
                "No keys provided. Please provide --values key key ... to delete from the profile file.")
            return

        if profile_path is None:
            # Error message already printed in open_profile
            return

        flatten_contents = flatten_dict(contents)

        for arg in values:
            key = arg
            if flatten_contents.__contains__(key):
                del flatten_contents[key]
                log_info(f"Variable {key} was removed from profile {config.profile.name}")
            else:
                log_warning(f"Variable {key} does not exist in profile {config.profile.name}")

        try:
            with open(profile_path, "w") as f:
                yaml.safe_dump(unflatten_dict(flatten_contents), f)
        except Exception as e:
            log_error_with_exception("Failed to write profile", e)

    @staticmethod
    def check_config(config: "bittensor.config"):
        profile = config.get("profile", {})
        name = profile.get("name")
        path = profile.get("path")
        # TODO: Check; This should never been possible because of the defaults which are set in the argument parser
        # Is there any case where this function is useful?
        return name is not None and path is not None

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        profile_parser = parser.add_parser("delete_value", help="""Delete profile values""")
        profile_parser.set_defaults(func=ProfileDeleteValueCommand.run)
        profile_parser.add_argument("--profile.name", type=str, help="The name of the profile to update")
        profile_parser.add_argument("--profile.path", type=str, default=defaults.profile.path,
                                    help="The path to the profile directory")
        profile_parser.add_argument("--values", nargs=argparse.REMAINDER, help="The keys to delete")


class ProfileUseCommand:
    @staticmethod
    def run(cli):
        config = cli.config
        profile_path, _contents = open_profile(cli)

        if profile_path is None:
            # Error message already printed in open_profile
            return

        try:
            file_path = os.path.join(os.path.expanduser(config.profile.path), '.btcliprofile')
            with open(file_path, 'w+') as file:
                file.write(config.profile.name)

            log_info(f"Profile {config.profile.name} set as active.")
        except Exception as e:
            log_error_with_exception("Failed to set active profile", e)

    @staticmethod
    def check_config(config: "bittensor.config"):
        profile = config.get("profile", {})
        name = profile.get("name")
        path = profile.get("path")
        # TODO: Check; This should never been possible because of the defaults which are set in the argument parser
        # Is there any case where this function is useful?
        return name is not None or path is not None

    @staticmethod
    def add_args(parser: argparse.ArgumentParser):
        profile_parser = parser.add_parser("use", help="""Use active profile""")
        profile_parser.set_defaults(func=ProfileUseCommand.run)
        profile_parser.add_argument("--profile.name", type=str, help="The name of the profile to use",
                                    default=defaults.profile.name)
        profile_parser.add_argument("--profile.path", type=str, default=defaults.profile.path,
                                    help="The path to the profile directory")
