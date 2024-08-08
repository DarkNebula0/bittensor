# Standard Library
import os
from unittest import mock
from unittest.mock import patch, MagicMock, mock_open

# 3rd Party
import pytest
import yaml
from rich.table import Table

# Bittensor
from bittensor.commands.profile import (
    ProfileCreateCommand,
    ProfileListCommand,
    ProfileShowCommand,
    ProfileDeleteCommand,
    ProfileSetValueCommand,
    ProfileDeleteValueCommand,
    ProfileUseCommand,
    list_profiles,
    get_profile_file_path,
    get_profile_path_from_config,
    open_profile,
)
from bittensor import config as bittensor_config


class MockDefaults:
    profile = {
        "name": "default",
        "path": "~/.bittensor/profiles/",
    }


@pytest.fixture
def mock_cli():
    mock_cli = MagicMock()
    mock_cli.config = bittensor_config()
    mock_cli.config.profile = MagicMock()
    mock_cli.config.profile.path = "~/.bittensor/profiles/"
    mock_cli.config.profile.name = "default"
    mock_cli.config.is_set = MagicMock(return_value=True)
    mock_cli.config.no_prompt = False
    mock_cli.config.values = None
    return mock_cli


def test_list_profiles_success():
    path = "/fake/path/"
    with patch("os.listdir", return_value=["profile1.yml", "profile2.yml"]), patch(
        "os.makedirs"
    ) as mock_makedirs:
        profiles = list_profiles(path)
        assert profiles == ["profile1.yml", "profile2.yml"]
        mock_makedirs.assert_called_once_with(path, exist_ok=True)


def test_list_profiles_no_profiles():
    path = "/fake/path/"
    with patch("os.listdir", return_value=[]), patch("os.makedirs"):
        profiles = list_profiles(path)
        assert profiles == []


def test_list_profiles_os_error():
    path = "/fake/path/"
    with patch("os.makedirs", side_effect=OSError("Error")), patch("os.listdir"):
        profiles = list_profiles(path)
        assert profiles == []


def test_get_profile_file_path():
    path = "/fake/path/"
    profile_name = "profile1"
    with patch(
        "bittensor.commands.profile.list_profiles",
        return_value=["profile1.yml", "profile2.yml"],
    ):
        profile_path = get_profile_file_path(path, profile_name)
        expected_path = os.path.join(path, "profile1.yml")
        assert profile_path == expected_path


def test_get_profile_file_path_not_found():
    path = "/fake/path/"
    with patch(
        "bittensor.commands.profile.list_profiles",
        return_value=["profile1.yml", "profile2.yml"],
    ):
        profile_path = get_profile_file_path(path, "profile3")
        assert profile_path is None


def test_get_profile_path_from_config(mock_cli):
    mock_cli.config.profile.path = "/fake/path/"
    mock_cli.config.profile.name = "profile1"
    with patch(
        "bittensor.commands.profile.list_profiles",
        return_value=["profile1.yml", "profile2.yml"],
    ):
        profile_path = get_profile_path_from_config(mock_cli)
        expected_path = os.path.join("/fake/path/", "profile1.yml")
        assert profile_path == expected_path


def test_open_profile(mock_cli):
    mock_cli.config.profile.name = "test_profile"
    with patch(
        "builtins.open", mock_open(read_data="profile:\n  name: test_profile")
    ), patch(
        "bittensor.commands.profile.get_profile_path_from_config",
        return_value="/fake/path/test_profile.yml",
    ):
        profile_path, contents = open_profile(mock_cli)
        assert profile_path == "/fake/path/test_profile.yml"
        assert contents == {"profile": {"name": "test_profile"}}


def test_open_profile_not_found(mock_cli):
    mock_cli.config.profile.name = "test_profile"
    with patch(
        "bittensor.commands.profile.get_profile_path_from_config", return_value=None
    ):
        profile_path, contents = open_profile(mock_cli)
        assert profile_path is None
        assert contents is None


def test_run_profile_command(mock_cli):
    with patch("bittensor.subtensor"), patch.object(
        ProfileCreateCommand, "_run"
    ) as mock_run:
        ProfileCreateCommand.run(mock_cli)
        mock_run.assert_called_once()


def test_profile_command_write_profile():
    mock_config = bittensor_config()
    mock_config.profile = MagicMock()
    mock_config.profile.path = "~/.bittensor/profiles/"
    mock_config.profile.name = "test_profile"
    with patch("os.makedirs"), patch(
        "os.path.expanduser", return_value="/.bittensor/profiles/"
    ), patch("builtins.open", mock_open()) as mock_file:
        ProfileCreateCommand._write_profile(
            mock_config, {"profile": {"name": "test_profile"}}
        )
        mock_file.assert_called_once_with("/.bittensor/profiles/test_profile.yml", "w+")


def test_profile_list_command(mock_cli):
    mock_cli.config.profile.path = "/fake/path/"
    with patch("os.listdir", return_value=["test_profile.yml"]), patch(
        "builtins.open",
        mock_open(
            read_data="profile:\n  name: test_profile\nsubtensor:\n  network: mainnet\nnetuid: 0"
        ),
    ), patch("bittensor.__console__.print"):
        ProfileListCommand.run(mock_cli)


def test_profile_show_command(mock_cli):
    mock_cli.config.profile.name = "test_profile"
    with patch(
        "builtins.open",
        mock_open(
            read_data="profile:\n  name: test_profile\nsubtensor:\n  network: mainnet\nnetuid: 0"
        ),
    ), patch(
        "bittensor.commands.profile.get_profile_path_from_config",
        return_value="/fake/path/test_profile.yml",
    ), patch(
        "bittensor.__console__.print"
    ):
        ProfileShowCommand.run(mock_cli)


def test_profile_delete_command(mock_cli):
    mock_cli.config.profile.name = "test_profile"
    mock_cli.config.profile.path = "/fake/path/"
    profile_path = "/fake/path/test_profile.yml"

    with patch("os.remove") as mock_remove, patch(
        "bittensor.commands.profile.get_profile_path_from_config",
        return_value=profile_path,
    ), patch(
        "builtins.open", mock_open(read_data="profile:\n  name: test_profile")
    ), patch(
        "bittensor.commands.profile.Prompt.ask", return_value="y"
    ), patch(
        "bittensor.commands.profile.log_info"
    ) as mock_log_info, patch(
        "bittensor.commands.profile.log_error_with_exception"
    ) as mock_log_error:
        # Run the command
        ProfileDeleteCommand._run(mock_cli)

        # Check if the profile was deleted
        mock_remove.assert_called_once_with("/fake/path/test_profile.yml")
        mock_log_info.assert_called_once_with(
            f"Profile {mock_cli.config.profile.name} deleted from {os.path.expanduser(mock_cli.config.profile.path)}"
        )
        mock_log_error.assert_not_called()


def test_profile_set_value_command(mock_cli):
    mock_cli.config["values"] = ["profile.name=new_name"]
    with patch(
        "builtins.open", mock_open(read_data="profile:\n  name: test_profile")
    ), patch(
        "bittensor.commands.profile.get_profile_path_from_config",
        return_value="/fake/path/test_profile.yml",
    ), patch(
        "bittensor.__console__.print"
    ):
        ProfileSetValueCommand.run(mock_cli)


def test_profile_delete_value_command(mock_cli):
    mock_cli.config["values"] = ["profile.name"]
    profile_path = "/fake/path/test_profile.yml"
    profile_data = {"profile": {"name": "test_profile"}}
    flatten_contents = {"profile.name": "test_profile"}

    with patch(
        "bittensor.commands.profile.open_profile",
        return_value=(profile_path, profile_data),
    ), patch(
        "bittensor.commands.profile.get_profile_path_from_config",
        return_value=profile_path,
    ), patch(
        "bittensor.commands.profile.Prompt.ask", return_value="y"
    ), patch(
        "bittensor.commands.profile.flatten_dict", return_value=flatten_contents
    ), patch(
        "bittensor.commands.profile.unflatten_dict",
        return_value={"profile": {"name": None}},
    ), patch(
        "bittensor.commands.profile.log_info"
    ) as mock_log_info, patch(
        "bittensor.commands.profile.log_warning"
    ) as mock_log_warning, patch(
        "bittensor.commands.profile.log_error"
    ) as mock_log_error, patch(
        "bittensor.commands.profile.log_error_with_exception"
    ) as mock_log_error_with_exception, patch(
        "bittensor.__console__.print"
    ):
        # Mocking the open function to simulate file writing
        with patch("builtins.open", mock_open()) as mocked_open:
            # Run the command
            ProfileDeleteValueCommand._run(mock_cli)

            mock_log_error.assert_not_called()

            # Ensure the file was written correctly
            mocked_open.assert_called_once_with(profile_path, "w")
            handle = mocked_open()

            # Aggregate the write calls
            written_data = "".join(call.args[0] for call in handle.write.call_args_list)
            expected_data = yaml.safe_dump({"profile": {"name": None}})
            assert written_data == expected_data

        # Check that log_info was called
        mock_log_info.assert_called_once_with(
            f"Variable profile.name was removed from profile {mock_cli.config.profile.name}"
        )

        mock_log_warning.assert_not_called()
        mock_log_error.assert_not_called()
        mock_log_error_with_exception.assert_not_called()


def test_profile_show_command_format(mock_cli):
    mock_cli.config.profile.name = "test_profile"
    with patch(
        "builtins.open",
        mock_open(
            read_data="profile:\n  name: test_profile\nsubtensor:\n  network: mainnet\nnetuid: 0"
        ),
    ), patch(
        "bittensor.commands.profile.get_profile_path_from_config",
        return_value="/fake/path/test_profile.yml",
    ), patch(
        "bittensor.__console__.print"
    ) as mock_print:
        ProfileShowCommand.run(mock_cli)

        printed_table = mock_print.call_args[0][0]
        assert isinstance(printed_table, Table)

        assert printed_table.title == "[white]Profile [bold white]test_profile"

        columns = [column.header for column in printed_table.columns]
        assert columns == ["[overline white]PARAMETERS", "[overline white]VALUES"]

        param_cells = printed_table.columns[0]._cells
        value_cells = printed_table.columns[1]._cells
        rows = list(zip(param_cells, value_cells))

        expected_rows = [
            ("  [bold white]profile.name", "[green]test_profile"),
            ("  [bold white]subtensor.network", "[green]mainnet"),
            ("  [bold white]netuid", "[green]0"),
        ]
        assert rows == expected_rows


def test_profile_list_command_format(mock_cli):
    mock_cli.config.profile.path = "/fake/path/"
    with patch("os.listdir", return_value=["test_profile.yml"]), patch(
        "builtins.open",
        mock_open(
            read_data="profile:\n  name: test_profile\nsubtensor:\n  network: mainnet\nnetuid: 0"
        ),
    ), patch("bittensor.__console__.print") as mock_print, patch(
        "os.makedirs", return_value=True
    ):
        ProfileListCommand.run(mock_cli)

        printed_table = mock_print.call_args[0][0]
        assert isinstance(printed_table, Table)

        assert printed_table.title == "[white]Profiles"

        columns = [column.header for column in printed_table.columns]
        assert columns == ["Active", "Name"]

        active_cells = printed_table.columns[0]._cells
        name_cells = printed_table.columns[1]._cells
        rows = list(zip(active_cells, name_cells))

        expected_rows = [
            ("", "test_profile"),
        ]
        assert rows == expected_rows


def test_profile_use_command(mock_cli):
    mock_cli.config.profile.name = "test_profile"
    mock_cli.config.profile.path = "/fake/path/"
    with patch(
        "builtins.open", mock_open(read_data="profile:\n  name: test_profile")
    ), patch(
        "bittensor.commands.profile.get_profile_path_from_config",
        return_value="/fake/path/test_profile.yml",
    ), patch(
        "bittensor.__console__.print"
    ), patch(
        "os.path.exists", return_value=True
    ), patch(
        "yaml.safe_load", return_value={"profile": {"active": "old_profile"}}
    ), patch(
        "yaml.safe_dump"
    ) as mock_safe_dump, patch(
        "builtins.open", mock_open()
    ) as mock_open_file:
        ProfileUseCommand.run(mock_cli)

        mock_open_file.assert_any_call(
            os.path.join(
                os.path.expanduser(mock_cli.config.profile.path), ".btcliprofile"
            ),
            "w+",
        )
        mock_open_file().write.assert_called_once_with("test_profile")
