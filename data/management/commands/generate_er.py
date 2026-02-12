# SPDX-License-Identifier: MIT
# Copyright (c) 2025 horohoro-dev
#
# Inspired by django-erd-generator by Andryo Marzuki
# https://pypi.org/project/django-erd-generator/

"""
Django Management Command to generate Mermaid ER diagrams with help_text and data dictionary.

Usage:
    python manage.py generate_er                # Output to docs/er-diagram.md
    python manage.py generate_er -o output.md   # Output to specified file
    python manage.py generate_er --stdout       # Print to stdout
    python manage.py generate_er -a app1,app2   # Target multiple apps
    python manage.py generate_er -w             # Include warnings in markdown
"""

from dataclasses import dataclass
from pathlib import Path

from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import ForeignKey
from django.db.models.fields.related import OneToOneField


@dataclass
class DeprecationWarning:
    """Warning for deprecated patterns."""
    model_name: str
    field_name: str | None
    issue: str
    recommendation: str


# Warning messages in English and Japanese
WARNING_MESSAGES = {
    "unique_together": {
        "en": {
            "issue": "unique_together = {value}",
            "recommendation": "Use Meta.constraints with UniqueConstraint instead",
        },
        "ja": {
            "issue": "unique_together = {value}",
            "recommendation": "Meta.constraintsとUniqueConstraintを使用してください",
        },
    },
    "fk_unique": {
        "en": {
            "issue": "ForeignKey with unique=True",
            "recommendation": "Use OneToOneField instead",
        },
        "ja": {
            "issue": "ForeignKey(unique=True)",
            "recommendation": "OneToOneFieldを使用してください",
        },
    },
}


class Command(BaseCommand):
    help = "Generate ER diagram with help_text and data dictionary"

    DEFAULT_OUTPUT_DIR = "docs"
    DEFAULT_OUTPUT_FILE = "er-diagram.md"

    def add_arguments(self, parser):
        parser.add_argument(
            "-a",
            "--apps",
            required=False,
            default=None,
            help='Apps to include. If not specified, uses the app where this command is located.',
        )
        parser.add_argument(
            "-o",
            "--output",
            required=False,
            default=None,
            help=f"Output file path. Defaults to {self.DEFAULT_OUTPUT_DIR}/{self.DEFAULT_OUTPUT_FILE}",
        )
        parser.add_argument(
            "--to-stdout",
            action="store_true",
            help="Print to stdout instead of file.",
        )
        parser.add_argument(
            "-w",
            "--include-warnings",
            action="store_true",
            help="Include deprecation warnings in the output markdown file.",
        )
        parser.add_argument(
            "-j",
            "--japanese",
            action="store_true",
            help="Output warnings in Japanese (requires -w).",
        )

    def _get_default_app_name(self) -> str:
        """Auto-detect app name from command file path."""
        # __file__: data/management/commands/generate_er.py
        # 3 levels up is the app directory
        command_path = Path(__file__).resolve()
        app_dir = command_path.parent.parent.parent
        return app_dir.name

    def _parse_apps(self, apps: str | None) -> list[str]:
        if not apps:
            return [self._get_default_app_name()]
        return [i.strip() for i in apps.split(",")]

    def _get_models(self, app_names: list[str] | None):
        """Get models from specified apps (handles GenericForeignKey)."""
        models = []
        for app_name in app_names:
            try:
                app_config = apps.get_app_config(app_name)
                for model in app_config.get_models():
                    # Skip proxy models
                    if model._meta.proxy:
                        continue
                    models.append(model)
            except LookupError:
                pass
        return models

    def _get_field_data_type(self, field) -> str:
        """Get database data type for a field."""
        try:
            db_type = field.cast_db_type(connection)
            if db_type:
                # Replace spaces with underscores for Mermaid compatibility
                return db_type.lower().replace(" ", "_").split("(")[0]
        except Exception:
            pass
        return field.__class__.__name__.lower()

    def _is_generic_field(self, field) -> bool:
        """Check if field is GenericForeignKey or GenericRelation."""
        return isinstance(field, (GenericForeignKey, GenericRelation))

    def _check_deprecations(self, app_names: list[str], japanese: bool = False) -> list[DeprecationWarning]:
        """Detect deprecated patterns in models."""
        warnings = []
        models = self._get_models(app_names)
        lang = "ja" if japanese else "en"

        for model in models:
            model_name = model.__name__
            meta = model._meta

            # Detect unique_together
            if meta.unique_together:
                msg = WARNING_MESSAGES["unique_together"][lang]
                warnings.append(DeprecationWarning(
                    model_name=model_name,
                    field_name=None,
                    issue=msg["issue"].format(value=meta.unique_together),
                    recommendation=msg["recommendation"],
                ))

            for field in meta.get_fields():
                if not hasattr(field, "attname"):
                    continue

                # Detect ForeignKey(unique=True), excluding OneToOneField
                if isinstance(field, ForeignKey) and not isinstance(field, OneToOneField) and getattr(field, "unique", False):
                    msg = WARNING_MESSAGES["fk_unique"][lang]
                    warnings.append(DeprecationWarning(
                        model_name=model_name,
                        field_name=field.name,
                        issue=msg["issue"],
                        recommendation=msg["recommendation"],
                    ))

        return warnings

    def _generate_warnings_markdown(self, warnings: list[DeprecationWarning], japanese: bool = False) -> str:
        """Generate warnings in Markdown format."""
        if not warnings:
            return ""

        if japanese:
            lines = [
                "# 非推奨パターンの警告\n",
                "以下の非推奨パターンが検出されました:\n",
                "| モデル | フィールド | 問題 | 推奨 |",
                "|--------|------------|------|------|",
            ]
        else:
            lines = [
                "# Deprecation Warnings\n",
                "The following deprecated patterns were detected:\n",
                "| Model | Field | Issue | Recommendation |",
                "|-------|-------|-------|----------------|",
            ]

        for w in warnings:
            field = w.field_name or "(Meta)"
            lines.append(f"| {w.model_name} | {field} | {w.issue} | {w.recommendation} |")

        lines.append("")
        return "\n".join(lines)

    def _generate_mermaid_with_helptext(self, app_names: list[str] | None) -> str:
        """Generate Mermaid ER diagram with help_text annotations."""
        models = self._get_models(app_names)
        lines = ["```mermaid", "erDiagram"]

        # Entity definitions
        for model in models:
            model_name = model.__name__
            lines.append(f"    {model_name} {{")

            for field in model._meta.get_fields():
                # Skip GenericForeignKey/GenericRelation
                if self._is_generic_field(field):
                    continue

                # Skip reverse relation fields (fields without attname)
                if not hasattr(field, "attname"):
                    continue

                col_name = field.attname
                data_type = self._get_field_data_type(field)
                help_text = getattr(field, "help_text", "") or ""

                # PK marker
                pk_mark = "PK" if field.primary_key else ""
                # FK marker
                if hasattr(field, "related_model") and field.related_model:
                    pk_mark = "FK" if not pk_mark else "PK,FK"

                # Add help_text as comment
                comment = f'"{help_text}"' if help_text else ""
                lines.append(
                    f"        {data_type} {col_name} {pk_mark} {comment}".rstrip()
                )

            lines.append("    }")

        # Relationships (use set to prevent duplicates)
        seen_relationships = set()

        for model in models:
            model_name = model.__name__

            # Get relations directly from model fields
            for field in model._meta.get_fields():
                # Skip GenericForeignKey/GenericRelation
                if self._is_generic_field(field):
                    continue

                # Only process ForeignKey, OneToOneField, ManyToManyField
                if not hasattr(field, "related_model") or field.related_model is None:
                    continue

                # Skip reverse relations (via related_name)
                if not hasattr(field, "attname") and not hasattr(field, "m2m_field_name"):
                    continue

                related_model_name = field.related_model.__name__
                field_name = field.name

                # Key for duplicate check (sorted to treat both directions as same)
                rel_key = tuple(sorted([model_name, related_model_name])) + (field_name,)

                # Skip duplicates for OneToOne and ManyToMany
                if field.one_to_one or field.many_to_many:
                    if rel_key in seen_relationships:
                        continue
                    seen_relationships.add(rel_key)

                # Connector symbol based on relation type
                if field.one_to_one:
                    connector = "||--||"
                elif field.many_to_many:
                    connector = "}o--o{"
                else:  # ForeignKey (many_to_one)
                    # 左側: 常に }o (子は0件以上、DBで最小数は強制不可)
                    # 右側: null=True → o| (親なしOK), null=False → || (親必須)
                    if getattr(field, "null", False):
                        connector = "}o--o|"
                    else:
                        connector = "}o--||"

                lines.append(
                    f"    {model_name} {connector} {related_model_name} : \"{field_name}\""
                )

        lines.append("```")
        return "\n".join(lines)

    def _generate_data_dictionary(self, app_names: list[str] | None) -> str:
        """Generate data dictionary (handles GenericForeignKey)."""
        models = self._get_models(app_names)
        lines = ["# Data Dictionary\n"]

        for model in sorted(models, key=lambda m: m.__name__):
            model_name = model.__name__
            doc_string = (model.__doc__ or "").strip()

            # Model header
            lines.append(f"## {model_name}\n")
            if doc_string and not doc_string.startswith(model_name):
                lines.append(f"{doc_string}\n")

            # Table header
            lines.append("| Field | Type | PK | FK | Null | Unique | Description |")
            lines.append("|-------|------|----|----|------|--------|-------------|")

            for field in model._meta.get_fields():
                # Skip GenericForeignKey/GenericRelation
                if self._is_generic_field(field):
                    continue

                # Skip reverse relation fields
                if not hasattr(field, "attname"):
                    continue

                col_name = field.attname
                data_type = self._get_field_data_type(field)
                pk = "✓" if field.primary_key else ""
                fk = "✓" if hasattr(field, "related_model") and field.related_model else ""
                null = "✓" if getattr(field, "null", False) else ""
                unique = "✓" if getattr(field, "unique", False) else ""
                help_text = getattr(field, "help_text", "") or ""

                lines.append(f"| {col_name} | {data_type} | {pk} | {fk} | {null} | {unique} | {help_text} |")

            lines.append("")

        return "\n".join(lines)

    def _get_output_path(self, output: str | None, use_stdout: bool) -> Path | None:
        """Determine output path."""
        if use_stdout:
            return None

        if output:
            return Path(output)

        # Default: docs/er-diagram.md
        return Path(self.DEFAULT_OUTPUT_DIR) / self.DEFAULT_OUTPUT_FILE

    def handle(self, *args, **options):
        app_names = self._parse_apps(options["apps"])
        output_path = self._get_output_path(options["output"], options["to_stdout"])
        include_warnings = options["include_warnings"]
        japanese = options["japanese"]

        self.stdout.write(f"Target apps: {', '.join(app_names)}")

        # Detect deprecated patterns
        warnings = self._check_deprecations(app_names, japanese=japanese)

        # Output warnings to console
        if warnings:
            self.stdout.write(self.style.WARNING(f"\nFound {len(warnings)} deprecation warning(s):"))
            for w in warnings:
                field_info = f".{w.field_name}" if w.field_name else ""
                self.stdout.write(self.style.WARNING(
                    f"  - {w.model_name}{field_info}: {w.issue}"
                ))
                self.stdout.write(f"    → {w.recommendation}")
            self.stdout.write("")

        # Generate Markdown
        mermaid = self._generate_mermaid_with_helptext(app_names)
        data_dict = self._generate_data_dictionary(app_names)

        content_parts = [
            "# ER Diagram\n",
            mermaid,
            "\n---\n",
            data_dict,
        ]

        # Add warnings to markdown only when option is specified
        if include_warnings and warnings:
            warnings_md = self._generate_warnings_markdown(warnings, japanese=japanese)
            content_parts.insert(0, warnings_md + "\n---\n")

        content = "\n".join(content_parts)

        if output_path:
            # Create directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Generated: {output_path}"))
        else:
            self.stdout.write(content)
