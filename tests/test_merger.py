"""Тесты для core/merger.py: маркер-мёрж и идемпотентность."""

import unittest

from repo_ctx.core.merger import (
    START,
    END,
    apply_marker_block,
    extract_managed_content,
    has_marker_block,
)


class TestHasMarkerBlock(unittest.TestCase):
    def test_no_markers(self):
        self.assertFalse(has_marker_block("просто текст"))

    def test_both_markers(self):
        text = f"{START}\ncontент\n{END}"
        self.assertTrue(has_marker_block(text))

    def test_only_start_marker(self):
        self.assertFalse(has_marker_block(f"{START}\nтекст"))

    def test_only_end_marker(self):
        self.assertFalse(has_marker_block(f"текст\n{END}"))


class TestExtractManagedContent(unittest.TestCase):
    def test_returns_none_without_markers(self):
        self.assertIsNone(extract_managed_content("текст без маркеров"))

    def test_extracts_content_between_markers(self):
        text = f"до\n{START}\nуправляемый контент\n{END}\nпосле"
        self.assertEqual(extract_managed_content(text), "управляемый контент")

    def test_extracts_multiline_content(self):
        content = "строка 1\nстрока 2\nстрока 3"
        text = f"{START}\n{content}\n{END}"
        self.assertEqual(extract_managed_content(text), content)


class TestApplyMarkerBlock(unittest.TestCase):
    def test_append_to_empty(self):
        result = apply_marker_block("", "новый контент")
        self.assertIn(START, result)
        self.assertIn(END, result)
        self.assertIn("новый контент", result)

    def test_append_to_existing_text_without_markers(self):
        result = apply_marker_block("существующий текст\n", "управляемое")
        self.assertTrue(result.startswith("существующий текст\n"))
        self.assertIn(START, result)
        self.assertIn("управляемое", result)

    def test_update_existing_block(self):
        original = f"до\n{START}\nстарый контент\n{END}\nпосле"
        result = apply_marker_block(original, "новый контент")
        self.assertIn("новый контент", result)
        self.assertNotIn("старый контент", result)

    def test_preserves_text_before_marker(self):
        before = "# Заголовок\n\nПользовательский текст\n\n"
        original = f"{before}{START}\nстарый\n{END}"
        result = apply_marker_block(original, "новый")
        self.assertTrue(result.startswith(before))

    def test_preserves_text_after_marker(self):
        after = "\n\nПользовательский текст после"
        original = f"{START}\nстарый\n{END}{after}"
        result = apply_marker_block(original, "новый")
        self.assertTrue(result.endswith(after))

    def test_idempotent_same_content(self):
        """Повторное применение с тем же контентом не меняет результат."""
        first = apply_marker_block("", "контент")
        second = apply_marker_block(first, "контент")
        self.assertEqual(first, second)

    def test_idempotent_with_surrounding_text(self):
        """Идемпотентность сохраняется с текстом до и после блока."""
        base = "до\n"
        after = "\nпосле"
        original = f"{base}{START}\nконтент\n{END}{after}"
        result = apply_marker_block(original, "контент")
        self.assertEqual(original, result)

    def test_extract_roundtrip(self):
        """Записанное содержимое можно извлечь обратно без потерь."""
        content = "строка А\nстрока Б"
        result = apply_marker_block("", content)
        extracted = extract_managed_content(result)
        self.assertEqual(extracted, content)


if __name__ == "__main__":
    unittest.main()
