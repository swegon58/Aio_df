from deerflow.config.paths import get_paths


def test_user_persona_file_is_under_user_dir() -> None:
    paths = get_paths()
    persona_path = paths.user_persona_file("alice")
    assert persona_path == paths.user_dir("alice") / "persona.json"
