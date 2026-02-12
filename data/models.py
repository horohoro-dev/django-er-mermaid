"""
generate_erd_full.py のテスト用モデル定義

様々なリレーション、フィールドタイプ、オプションを網羅
"""

import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


# =============================================================================
# Choices
# =============================================================================
class Status(models.TextChoices):
    """Status choices"""
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    ARCHIVED = "ARCHIVED", "Archived"


class Priority(models.IntegerChoices):
    """Priority choices"""
    LOW = 1, "Low"
    MEDIUM = 2, "Medium"
    HIGH = 3, "High"


# =============================================================================
# Basic Model (no relations)
# =============================================================================
class Tag(models.Model):
    """Tag model without relations"""
    name = models.CharField(max_length=50, unique=True, help_text="Tag name")
    slug = models.SlugField(max_length=50, unique=True, help_text="URL slug")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created at")

    def __str__(self):
        return self.name


# =============================================================================
# ForeignKey (Many-to-One)
# =============================================================================
class Category(models.Model):
    """Category with self-referential ForeignKey"""
    name = models.CharField(max_length=100, help_text="Category name")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent category (self-referential)",
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created at")

    def __str__(self):
        return self.name


class Author(models.Model):
    """Author model"""
    name = models.CharField(max_length=255, help_text="Author name")
    email = models.EmailField(unique=True, help_text="Email address")
    bio = models.TextField(blank=True, default="", help_text="Biography")
    is_active = models.BooleanField(default=True, help_text="Is active")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created at")

    def __str__(self):
        return self.name


class Article(models.Model):
    """Article with ForeignKey to Author and Category"""
    title = models.CharField(max_length=255, help_text="Article title")
    slug = models.SlugField(max_length=255, unique=True, help_text="URL slug")
    content = models.TextField(help_text="Article content")
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="articles",
        help_text="Article author",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
        help_text="Article category",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        help_text="Article status",
    )
    view_count = models.PositiveIntegerField(default=0, help_text="View count")
    published_at = models.DateTimeField(null=True, blank=True, help_text="Published at")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created at")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated at")

    def __str__(self):
        return self.title


# =============================================================================
# OneToOneField
# =============================================================================
class Profile(models.Model):
    """Profile with OneToOneField to Author"""
    author = models.OneToOneField(
        Author,
        on_delete=models.CASCADE,
        related_name="profile",
        help_text="Associated author",
    )
    avatar_url = models.URLField(blank=True, default="", help_text="Avatar URL")
    website = models.URLField(blank=True, default="", help_text="Website URL")
    location = models.CharField(max_length=100, blank=True, default="", help_text="Location")
    birth_date = models.DateField(null=True, blank=True, help_text="Birth date")

    def __str__(self):
        return f"Profile of {self.author.name}"


# =============================================================================
# ManyToManyField
# =============================================================================
class ArticleTag(models.Model):
    """Intermediate model for Article-Tag relation (explicit through)"""
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        help_text="Article",
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        help_text="Tag",
    )
    added_at = models.DateTimeField(auto_now_add=True, help_text="Added at")

    class Meta:
        unique_together = ("article", "tag")

    def __str__(self):
        return f"{self.article.title} - {self.tag.name}"


class Book(models.Model):
    """Book with ManyToManyField (implicit through)"""
    title = models.CharField(max_length=255, help_text="Book title")
    isbn = models.CharField(max_length=13, unique=True, help_text="ISBN-13")
    authors = models.ManyToManyField(
        Author,
        related_name="books",
        help_text="Book authors",
    )
    tags = models.ManyToManyField(
        Tag,
        through="BookTag",
        related_name="books",
        help_text="Book tags",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price")
    published_date = models.DateField(help_text="Published date")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created at")

    def __str__(self):
        return self.title


class BookTag(models.Model):
    """Intermediate model for Book-Tag relation (explicit through)"""
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        help_text="Book",
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        help_text="Tag",
    )
    relevance = models.PositiveSmallIntegerField(default=0, help_text="Relevance score")

    class Meta:
        unique_together = ("book", "tag")


# =============================================================================
# Various Field Types
# =============================================================================
class AllFieldTypes(models.Model):
    """Model with various field types for testing"""
    # String fields
    char_field = models.CharField(max_length=100, help_text="CharField")
    text_field = models.TextField(help_text="TextField")
    slug_field = models.SlugField(help_text="SlugField")
    email_field = models.EmailField(help_text="EmailField")
    url_field = models.URLField(help_text="URLField")
    uuid_field = models.UUIDField(help_text="UUIDField")

    # Numeric fields
    int_field = models.IntegerField(help_text="IntegerField")
    big_int_field = models.BigIntegerField(help_text="BigIntegerField")
    small_int_field = models.SmallIntegerField(help_text="SmallIntegerField")
    positive_int_field = models.PositiveIntegerField(help_text="PositiveIntegerField")
    positive_small_int_field = models.PositiveSmallIntegerField(help_text="PositiveSmallIntegerField")
    float_field = models.FloatField(help_text="FloatField")
    decimal_field = models.DecimalField(max_digits=10, decimal_places=2, help_text="DecimalField")

    # Boolean fields
    bool_field = models.BooleanField(default=False, help_text="BooleanField")

    # Date/Time fields
    date_field = models.DateField(help_text="DateField")
    datetime_field = models.DateTimeField(help_text="DateTimeField")
    time_field = models.TimeField(help_text="TimeField")
    duration_field = models.DurationField(help_text="DurationField")

    # Binary fields
    binary_field = models.BinaryField(help_text="BinaryField")

    # File fields (as path strings for testing)
    file_path_field = models.FilePathField(path="/tmp", help_text="FilePathField")

    # JSON field
    json_field = models.JSONField(default=dict, help_text="JSONField")

    # IP Address
    ip_field = models.GenericIPAddressField(help_text="GenericIPAddressField")

    def __str__(self):
        return f"AllFieldTypes #{self.pk}"


# =============================================================================
# Edge Cases
# =============================================================================
class EmptyModel(models.Model):
    """Model with only auto-generated id field"""
    pass


class ModelWithLongName(models.Model):
    """Model with very long field names and help texts"""
    this_is_a_very_long_field_name_that_might_cause_issues = models.CharField(
        max_length=255,
        help_text="This is a very long help text that describes what this field is used for in great detail",
    )


class Task(models.Model):
    """Task model with IntegerChoices"""
    title = models.CharField(max_length=255, help_text="Task title")
    description = models.TextField(blank=True, default="", help_text="Task description")
    priority = models.IntegerField(
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text="Task priority",
    )
    due_date = models.DateTimeField(null=True, blank=True, help_text="Due date")
    completed = models.BooleanField(default=False, help_text="Is completed")
    assigned_to = models.ForeignKey(
        Author,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
        help_text="Assigned author",
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created at")

    def __str__(self):
        return self.title


# =============================================================================
# Multiple ForeignKeys to same model
# =============================================================================
class Comment(models.Model):
    """Comment with multiple ForeignKeys"""
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="comments",
        help_text="Commented article",
    )
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="comments",
        help_text="Comment author",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text="Parent comment (for nested replies)",
    )
    content = models.TextField(help_text="Comment content")
    is_approved = models.BooleanField(default=False, help_text="Is approved")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created at")

    def __str__(self):
        return f"Comment by {self.author.name} on {self.article.title}"


# =============================================================================
# ManyToManyField (symmetrical=False) - Follow/Follower relationship
# =============================================================================
class UserFollow(models.Model):
    """User follow relationship (asymmetric M2M)"""
    follower = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="following",
        help_text="Follower",
    )
    following = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name="followers",
        help_text="Following",
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Followed at")

    class Meta:
        unique_together = ("follower", "following")

    def __str__(self):
        return f"{self.follower.name} follows {self.following.name}"


# =============================================================================
# GenericForeignKey (ContentTypes)
# =============================================================================
class Attachment(models.Model):
    """Attachment with GenericForeignKey"""
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Content type",
    )
    object_id = models.PositiveIntegerField(help_text="Object ID")
    content_object = GenericForeignKey("content_type", "object_id")

    file_name = models.CharField(max_length=255, help_text="File name")
    file_url = models.URLField(help_text="File URL")
    file_size = models.PositiveIntegerField(help_text="File size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True, help_text="Uploaded at")

    def __str__(self):
        return self.file_name


class ArticleWithAttachments(models.Model):
    """Article that can have generic attachments"""
    title = models.CharField(max_length=255, help_text="Title")
    attachments = GenericRelation(Attachment, help_text="Attachments")

    def __str__(self):
        return self.title


# =============================================================================
# ForeignKey to AUTH_USER_MODEL
# =============================================================================
class UserActivity(models.Model):
    """Activity log with FK to AUTH_USER_MODEL"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities",
        help_text="User",
    )
    action = models.CharField(max_length=100, help_text="Action performed")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="Timestamp")

    def __str__(self):
        return f"{self.user} - {self.action}"


# =============================================================================
# Model Inheritance - Abstract Base Model
# =============================================================================
class TimestampMixin(models.Model):
    """Abstract model with timestamp fields"""
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created at")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated at")

    class Meta:
        abstract = True


class Post(TimestampMixin):
    """Post inheriting from abstract TimestampMixin"""
    title = models.CharField(max_length=255, help_text="Post title")
    body = models.TextField(help_text="Post body")

    def __str__(self):
        return self.title


# =============================================================================
# Model Inheritance - Multi-table Inheritance
# =============================================================================
class Place(models.Model):
    """Base model for multi-table inheritance"""
    name = models.CharField(max_length=100, help_text="Place name")
    address = models.CharField(max_length=255, help_text="Address")

    def __str__(self):
        return self.name


class Restaurant(Place):
    """Restaurant inheriting from Place (multi-table)"""
    serves_pizza = models.BooleanField(default=False, help_text="Serves pizza")
    serves_pasta = models.BooleanField(default=False, help_text="Serves pasta")
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Rating (0-5)",
    )

    def __str__(self):
        return f"Restaurant: {self.name}"


# =============================================================================
# Model Inheritance - Proxy Model
# =============================================================================
class PublishedArticleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Status.PUBLISHED)


class PublishedArticle(Article):
    """Proxy model for published articles only"""
    objects = PublishedArticleManager()

    class Meta:
        proxy = True

    def __str__(self):
        return f"[Published] {self.title}"


# =============================================================================
# Additional Field Types
# =============================================================================
class MoreFieldTypes(models.Model):
    """Model with additional field types"""
    # Auto fields (explicit)
    # Note: Usually not needed as Django adds id automatically

    # File fields
    file_field = models.FileField(
        upload_to="uploads/",
        blank=True,
        null=True,
        help_text="FileField",
    )
    image_field = models.ImageField(
        upload_to="images/",
        blank=True,
        null=True,
        help_text="ImageField",
    )

    # Additional numeric
    positive_big_int_field = models.PositiveBigIntegerField(
        default=0,
        help_text="PositiveBigIntegerField",
    )

    def __str__(self):
        return f"MoreFieldTypes #{self.pk}"


# =============================================================================
# Custom Primary Key
# =============================================================================
class UUIDModel(models.Model):
    """Model with UUID as primary key"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID primary key",
    )
    name = models.CharField(max_length=100, help_text="Name")

    def __str__(self):
        return self.name


class CustomPKModel(models.Model):
    """Model with custom string primary key"""
    code = models.CharField(
        max_length=20,
        primary_key=True,
        help_text="Custom code as primary key",
    )
    description = models.TextField(help_text="Description")

    def __str__(self):
        return self.code


class BigAutoPKModel(models.Model):
    """Model with BigAutoField primary key"""
    id = models.BigAutoField(primary_key=True, help_text="BigAutoField PK")
    name = models.CharField(max_length=100, help_text="Name")

    def __str__(self):
        return self.name


class SmallAutoPKModel(models.Model):
    """Model with SmallAutoField primary key"""
    id = models.SmallAutoField(primary_key=True, help_text="SmallAutoField PK")
    name = models.CharField(max_length=100, help_text="Name")

    def __str__(self):
        return self.name


# =============================================================================
# Field Options
# =============================================================================
class FieldOptionsModel(models.Model):
    """Model demonstrating various field options"""
    # db_column
    custom_column = models.CharField(
        max_length=100,
        db_column="my_custom_column",
        help_text="Field with custom db_column",
    )

    # db_index
    indexed_field = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Field with db_index",
    )

    # db_comment (Django 4.2+)
    commented_field = models.CharField(
        max_length=100,
        db_comment="This is a database comment",
        help_text="Field with db_comment",
    )

    # validators
    validated_field = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Field with validators (0-100)",
    )

    # editable
    non_editable_field = models.CharField(
        max_length=100,
        editable=False,
        default="readonly",
        help_text="Non-editable field",
    )

    # db_default (Django 5.0+)
    db_default_field = models.CharField(
        max_length=100,
        db_default="default_value",
        help_text="Field with db_default",
    )

    def __str__(self):
        return f"FieldOptionsModel #{self.pk}"


# =============================================================================
# Meta Options
# =============================================================================
class MetaOptionsModel(models.Model):
    """Model demonstrating various Meta options"""
    name = models.CharField(max_length=100, help_text="Name")
    code = models.CharField(max_length=50, help_text="Code")
    category = models.CharField(max_length=50, help_text="Category")
    sort_order = models.IntegerField(default=0, help_text="Sort order")
    is_active = models.BooleanField(default=True, help_text="Is active")

    class Meta:
        db_table = "custom_table_name"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["name", "code"], name="name_code_idx"),
            models.Index(fields=["category"], name="category_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["name", "code"], name="unique_name_code"),
            models.CheckConstraint(condition=Q(sort_order__gte=0), name="positive_sort_order"),
        ]
        verbose_name = "Meta Options Model"
        verbose_name_plural = "Meta Options Models"

    def __str__(self):
        return self.name


# =============================================================================
# Composite Primary Key (Django 5.2+)
# Note: This requires Django 5.2 or later
# =============================================================================
# class CompositePKModel(models.Model):
#     """Model with composite primary key"""
#     pk = models.CompositePrimaryKey("tenant_id", "local_id")
#     tenant_id = models.IntegerField()
#     local_id = models.IntegerField()
#     name = models.CharField(max_length=100)
#
#     class Meta:
#         pass


# =============================================================================
# GeneratedField (Django 5.0+)
# =============================================================================
class GeneratedFieldModel(models.Model):
    """Model with GeneratedField"""
    first_name = models.CharField(max_length=100, help_text="First name")
    last_name = models.CharField(max_length=100, help_text="Last name")
    full_name = models.GeneratedField(
        expression=models.functions.Concat(
            F("first_name"), models.Value(" "), F("last_name")
        ),
        output_field=models.CharField(max_length=201),
        db_persist=True,
        help_text="Generated full name",
    )

    def __str__(self):
        return self.full_name


# =============================================================================
# On Delete Options
# =============================================================================
class OnDeleteCascade(models.Model):
    """Model with CASCADE on_delete"""
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        help_text="CASCADE - delete this when author is deleted",
    )
    name = models.CharField(max_length=100, help_text="Name")


class OnDeleteProtect(models.Model):
    """Model with PROTECT on_delete"""
    author = models.ForeignKey(
        Author,
        on_delete=models.PROTECT,
        help_text="PROTECT - prevent author deletion if this exists",
    )
    name = models.CharField(max_length=100, help_text="Name")


class OnDeleteSetNull(models.Model):
    """Model with SET_NULL on_delete"""
    author = models.ForeignKey(
        Author,
        on_delete=models.SET_NULL,
        null=True,
        help_text="SET_NULL - set to null when author is deleted",
    )
    name = models.CharField(max_length=100, help_text="Name")


class OnDeleteSetDefault(models.Model):
    """Model with SET_DEFAULT on_delete"""
    author = models.ForeignKey(
        Author,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        help_text="SET_DEFAULT - set to default when author is deleted",
    )
    name = models.CharField(max_length=100, help_text="Name")


class OnDeleteDoNothing(models.Model):
    """Model with DO_NOTHING on_delete"""
    author = models.ForeignKey(
        Author,
        on_delete=models.DO_NOTHING,
        help_text="DO_NOTHING - do nothing when author is deleted (DB may error)",
    )
    name = models.CharField(max_length=100, help_text="Name")


# =============================================================================
# DEPRECATED PATTERNS (for testing ERD generation)
# =============================================================================
class DeprecatedForeignKeyUnique(models.Model):
    """
    DEPRECATED: ForeignKey with unique=True
    Should use OneToOneField instead
    """
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        unique=True,  # DEPRECATED: Use OneToOneField instead
        related_name="deprecated_profile",
        help_text="ForeignKey with unique=True (should be OneToOneField)",
    )
    nickname = models.CharField(max_length=100, help_text="Nickname")

    class Meta:
        verbose_name = "Deprecated FK Unique"


# =============================================================================
# DEPRECATED: index_together (Cannot test - removed in Django 5.1)
# =============================================================================
# Django 6.0ではモデルロード時にエラーになるためテスト不可
# Django 5.0以前では以下のように定義できた：
#
# class DeprecatedIndexTogether(models.Model):
#     """
#     DEPRECATED: Using index_together instead of indexes
#     Deprecated in Django 4.1, removed in Django 5.1
#     """
#     first_name = models.CharField(max_length=100)
#     last_name = models.CharField(max_length=100)
#
#     class Meta:
#         index_together = [("first_name", "last_name")]
#
# 推奨される書き方：
#     class Meta:
#         indexes = [
#             models.Index(fields=["first_name", "last_name"], name="name_idx"),
#         ]
# =============================================================================


class DeprecatedUniqueTogether(models.Model):
    """
    DEPRECATED: Using unique_together instead of UniqueConstraint
    Still works but UniqueConstraint is recommended
    """
    code = models.CharField(max_length=50, help_text="Code")
    version = models.IntegerField(help_text="Version")
    name = models.CharField(max_length=100, help_text="Name")

    class Meta:
        # DEPRECATED: Use Meta.constraints with UniqueConstraint instead
        unique_together = [
            ("code", "version"),
        ]


# =============================================================================
# DATABASE ANTI-PATTERNS (for testing ERD generation)
# =============================================================================
class AntiPatternRepeatingColumns(models.Model):
    """
    ANTI-PATTERN: Repeating columns instead of separate table
    phone1, phone2, phone3 should be a separate PhoneNumber table
    """
    name = models.CharField(max_length=100, help_text="Name")
    phone1 = models.CharField(max_length=20, blank=True, default="", help_text="Phone 1")
    phone2 = models.CharField(max_length=20, blank=True, default="", help_text="Phone 2")
    phone3 = models.CharField(max_length=20, blank=True, default="", help_text="Phone 3")
    email1 = models.EmailField(blank=True, default="", help_text="Email 1")
    email2 = models.EmailField(blank=True, default="", help_text="Email 2")
    email3 = models.EmailField(blank=True, default="", help_text="Email 3")


class AntiPatternEAVAttribute(models.Model):
    """
    ANTI-PATTERN: Entity-Attribute-Value pattern
    Flexible but loses type safety and referential integrity
    """
    entity_type = models.CharField(max_length=100, help_text="Entity type (e.g., 'product', 'user')")
    entity_id = models.PositiveIntegerField(help_text="Entity ID")
    attribute_name = models.CharField(max_length=100, help_text="Attribute name")
    attribute_value = models.TextField(help_text="Attribute value (stored as text)")

    class Meta:
        indexes = [
            models.Index(fields=["entity_type", "entity_id"], name="eav_entity_idx"),
        ]


class AntiPatternGodTable(models.Model):
    """
    ANTI-PATTERN: God table / Monster table
    Too many columns, should be split into multiple tables
    """
    # User info
    username = models.CharField(max_length=100, help_text="Username")
    email = models.EmailField(help_text="Email")
    password_hash = models.CharField(max_length=255, help_text="Password hash")

    # Profile info (should be separate table)
    first_name = models.CharField(max_length=100, blank=True, default="", help_text="First name")
    last_name = models.CharField(max_length=100, blank=True, default="", help_text="Last name")
    bio = models.TextField(blank=True, default="", help_text="Bio")
    avatar_url = models.URLField(blank=True, default="", help_text="Avatar URL")

    # Address info (should be separate table)
    street = models.CharField(max_length=255, blank=True, default="", help_text="Street")
    city = models.CharField(max_length=100, blank=True, default="", help_text="City")
    state = models.CharField(max_length=100, blank=True, default="", help_text="State")
    postal_code = models.CharField(max_length=20, blank=True, default="", help_text="Postal code")
    country = models.CharField(max_length=100, blank=True, default="", help_text="Country")

    # Settings (should be separate table)
    theme = models.CharField(max_length=50, default="light", help_text="Theme")
    language = models.CharField(max_length=10, default="en", help_text="Language")
    timezone = models.CharField(max_length=50, default="UTC", help_text="Timezone")
    notifications_enabled = models.BooleanField(default=True, help_text="Notifications enabled")

    # Stats (should be separate table or computed)
    login_count = models.PositiveIntegerField(default=0, help_text="Login count")
    last_login = models.DateTimeField(null=True, blank=True, help_text="Last login")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created at")
    updated_at = models.DateTimeField(auto_now=True, help_text="Updated at")


class AntiPatternCircularRefA(models.Model):
    """
    ANTI-PATTERN: Circular reference (A -> B -> A)
    Can cause issues with deletion and data integrity
    """
    name = models.CharField(max_length=100, help_text="Name")
    ref_b = models.ForeignKey(
        "AntiPatternCircularRefB",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refs_from_a",
        help_text="Reference to B (circular)",
    )


class AntiPatternCircularRefB(models.Model):
    """
    ANTI-PATTERN: Circular reference (B -> A -> B)
    """
    name = models.CharField(max_length=100, help_text="Name")
    ref_a = models.ForeignKey(
        AntiPatternCircularRefA,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="refs_from_b",
        help_text="Reference to A (circular)",
    )


class AntiPatternSoftDelete(models.Model):
    """
    ANTI-PATTERN: Soft delete without proper handling
    is_deleted flag without proper constraints/indexes
    """
    name = models.CharField(max_length=100, help_text="Name")
    data = models.TextField(help_text="Data")
    is_deleted = models.BooleanField(default=False, help_text="Soft delete flag")
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Deleted at")
    # Missing: unique constraint considering is_deleted
    # Missing: index on is_deleted for filtering


class AntiPatternPolymorphicString(models.Model):
    """
    ANTI-PATTERN: Polymorphic association with string type
    Less safe than ContentTypes framework
    """
    parent_type = models.CharField(
        max_length=100,
        help_text="Parent type as string (e.g., 'article', 'book')",
    )
    parent_id = models.PositiveIntegerField(help_text="Parent ID")
    comment = models.TextField(help_text="Comment")
    # No referential integrity - parent_id is just a number


class AntiPatternImplicitDefaults(models.Model):
    """
    ANTI-PATTERN: Relying on implicit/database defaults
    Can cause issues when values differ between Django and DB
    """
    # CharField without explicit default - will be empty string in DB but None in Python
    optional_name = models.CharField(max_length=100, blank=True, help_text="Optional name without default")

    # Nullable field that should probably have a default
    count = models.IntegerField(null=True, help_text="Count without default")

    # Boolean without default (Django will complain)
    is_active = models.BooleanField(null=True, help_text="Is active without default")


class AntiPatternFloatMoney(models.Model):
    """
    ANTI-PATTERN: Using FloatField for money
    Should use DecimalField for precise calculations
    """
    product_name = models.CharField(max_length=100, help_text="Product name")
    # BAD: FloatField loses precision for money
    price_float = models.FloatField(help_text="Price as float (loses precision)")
    # GOOD: DecimalField for money
    price_decimal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price as decimal (correct)",
    )


class AntiPatternCommaList(models.Model):
    """
    ANTI-PATTERN: Storing lists as comma-separated values
    Should use ManyToManyField or ArrayField
    """
    name = models.CharField(max_length=100, help_text="Name")
    # BAD: Comma-separated list
    tags_csv = models.TextField(
        blank=True,
        default="",
        help_text="Tags as comma-separated values (should be M2M)",
    )
    # BAD: JSON array in TextField
    categories_json = models.TextField(
        blank=True,
        default="[]",
        help_text="Categories as JSON string (should use JSONField or M2M)",
    )


class AntiPatternNoIndex(models.Model):
    """
    ANTI-PATTERN: Frequently queried fields without indexes
    """
    # Frequently filtered but no index
    status = models.CharField(max_length=50, help_text="Status (frequently filtered, no index)")
    created_date = models.DateField(help_text="Created date (frequently filtered, no index)")
    # Frequently used in WHERE but no index
    external_id = models.CharField(max_length=100, help_text="External ID (frequently looked up, no index)")
    # Frequently sorted but no index
    priority = models.IntegerField(help_text="Priority (frequently sorted, no index)")
