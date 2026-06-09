"""Тесты для core/profile.py: эвристика, load_profile, list_profiles."""

import json
import os
import tempfile
import unittest

from repo_ctx.core.profile import detect_profile, list_profiles, load_profile
from repo_ctx.exceptions import ManifestError, ProfileNotFoundError


def _make_profile(standards_dir: str, name: str, data: dict) -> None:
    """Создаёт profile.json для профиля в тестовой директории standards."""
    profile_dir = os.path.join(standards_dir, "profiles", name)
    os.makedirs(profile_dir, exist_ok=True)
    with open(os.path.join(profile_dir, "profile.json"), "w") as f:
        json.dump(data, f)


class TestDetectProfile(unittest.TestCase):
    def test_dockerfile_gives_microservice(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "Dockerfile"), "w").close()
            self.assertEqual(detect_profile(d), "microservice")

    def test_roles_dir_gives_ansible_role(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "roles"))
            self.assertEqual(detect_profile(d), "ansible-role")

    def test_dockerfile_takes_priority_over_roles(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "Dockerfile"), "w").close()
            os.makedirs(os.path.join(d, "roles"))
            self.assertEqual(detect_profile(d), "microservice")

    def test_default_for_plain_directory(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(detect_profile(d), "default")


class TestLoadProfile(unittest.TestCase):
    def test_loads_valid_profile(self):
        with tempfile.TemporaryDirectory() as d:
            _make_profile(d, "microservice", {"context": ["ctx1"], "commands": []})
            result = load_profile("microservice", d)
        self.assertEqual(result["context"], ["ctx1"])

    def test_raises_profile_not_found(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ProfileNotFoundError):
                load_profile("nonexistent", d)

    def test_raises_on_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            profile_dir = os.path.join(d, "profiles", "bad")
            os.makedirs(profile_dir)
            with open(os.path.join(profile_dir, "profile.json"), "w") as f:
                f.write("{bad json")
            with self.assertRaises(ManifestError):
                load_profile("bad", d)


class TestListProfiles(unittest.TestCase):
    def test_returns_empty_when_no_profiles_dir(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(list_profiles(d), [])

    def test_lists_available_profiles(self):
        with tempfile.TemporaryDirectory() as d:
            _make_profile(d, "microservice", {})
            _make_profile(d, "ansible-role", {})
            result = list_profiles(d)
        self.assertIn("microservice", result)
        self.assertIn("ansible-role", result)

    def test_ignores_dirs_without_profile_json(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "profiles", "incomplete"))
            result = list_profiles(d)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
