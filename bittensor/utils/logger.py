import bittensor


def log_error_with_exception(message, exception):
    bittensor.__console__.print(f":cross_mark: [red]{message}[/red]:[bold white] {exception}")


def log_info(message):
    bittensor.__console__.print(f":white_check_mark: [bold green]{message}[/bold green]")


def log_warning(message):
    bittensor.__console__.print(f":warning: [yellow]{message}[/yellow]")


def log_error(message):
    bittensor.__console__.print(f":cross_mark: [red]{message}[/red]")
