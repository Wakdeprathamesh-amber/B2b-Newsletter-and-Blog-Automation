"""Enumerations used across all data models."""

from enum import StrEnum


class Region(StrEnum):
    UK = "UK"
    USA = "USA"
    AUSTRALIA = "Australia"
    CANADA = "Canada"
    EUROPE = "Europe"
    GLOBAL = "Global"


class TopicCategory(StrEnum):
    RENT_TRENDS = "Rent Trends"
    VISA_DATA = "Visa Data"
    STUDENT_DEMAND = "Student Demand"
    POLICY_CHANGES = "Policy Changes"
    SUPPLY_OUTLOOK = "Supply Outlook"
    EMERGING_MARKETS = "Emerging Markets"
    QS_RANKINGS = "QS Rankings"
    OTHER = "Other"


class StakeholderAudience(StrEnum):
    SUPPLY = "Supply"
    UNIVERSITY = "University"
    HEA = "HEA"


class UrgencyLevel(StrEnum):
    BREAKING = "Breaking"
    TIME_SENSITIVE = "Time-sensitive"
    EVERGREEN = "Evergreen"


class TopicStatus(StrEnum):
    PENDING = "Pending"
    APPROVED = "Approved"
    EDITED = "Edited"
    REJECTED = "Rejected"


class DraftChannel(StrEnum):
    LINKEDIN = "LinkedIn"
    BLOG = "Blog"
    NEWSLETTER = "Newsletter"


class DraftVoice(StrEnum):
    # LinkedIn voices
    AMBER_BRAND = "AmberBrand"
    MADHUR = "Madhur"
    JOOLS = "Jools"
    # Blog voices
    BLOG_SUPPLY = "BlogSupply"
    BLOG_UNIVERSITY = "BlogUniversity"
    BLOG_HEA = "BlogHEA"
    # Newsletter
    NEWSLETTER_GLOBAL = "NewsletterGlobal"


class DraftStatus(StrEnum):
    DRAFT = "Draft"
    UNDER_REVIEW = "UnderReview"
    REVISION_REQUESTED = "RevisionRequested"
    APPROVED = "Approved"
    PUBLISHED = "Published"
    BLOCKED = "Blocked"
    GENERATION_FAILED = "GenerationFailed"


class CycleStatus(StrEnum):
    RUNNING = "Running"
    AWAITING_TOPIC_APPROVAL = "AwaitingTopicApproval"
    AWAITING_CONTENT_REVIEW = "AwaitingContentReview"
    PUBLISHING = "Publishing"
    COMPLETE = "Complete"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class GateType(StrEnum):
    TOPIC_APPROVAL = "TopicApproval"
    CONTENT_REVIEW = "ContentReview"
